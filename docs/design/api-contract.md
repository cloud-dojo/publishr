# Publishr フロント⇔バックAPI契約（境界面スペック）

> 📑 全体の目次・真実源マップは [正本マップ](../README.md)／未確定論点は [open-issues.md](../planning/open-issues.md)。

> **位置づけ**: 役割分担（友人＝バック／鉄田＝フロント）の**境界面**を固める。`エージェントIO契約.md` §11で決めた「Firestore直アクセス＋薄いCloud Run API 3本」の方針を、**実装可能なreq/resスキーマ**に翻訳する。鉄田がフロントを、友人がAPIを、互いを待たずに並行実装できる状態にするのが目的。
> **原典**: 連携方式＝`エージェントIO契約.md` §11、データモデル＝`技術アーキテクチャ.md` §3、状態機械＝同。
> **担当**: API実装＝友人／フロント呼び出し＝鉄田。スキーマは本書で握る。
> **ステータス**: ✅ MTG 2026-06-05で §6の連携論点（G1-3/5/6/7・予約原子性I-20・トリガー認可）を確定し本書に反映済み。

---

## 1. 原則：Firestore直 vs API の住み分け

`エージェントIO契約.md` §11の再掲（正本）。**読み取りと低リスクな書き込みはFirestore直、バックエンド処理／機密はAPI。**

| 操作 | 方式 | 担当 |
|---|---|---|
| 棚(draft一覧)・本詳細・アジェンダ・読書本文メタの**読み取り** | Firestoreリアルタイム購読（API不要） | 鉄田 |
| ハイライト・簡易FB・★の**保存** | Firestore直書き（セキュリティルールで保護＝`Firestoreセキュリティルール.md`） | 鉄田 |
| **ユーザー初期登録**（initialProfile保存） | Firestore直書き（初回create・ルールで保護） | 鉄田 |
| **お気に入り著者の保存/削除** | Firestore直書き（`users/{uid}.favoriteAuthors[]` を arrayUnion/Remove） | 鉄田 |
| **予約**（draft→reserved＋執筆発火） | `POST /api/reserve`（Cloud Run） | 友人 |
| **OAuth連携**（Drive/Calendar/Tasksのトークン交換） | `GET /api/auth/google/*`（Cloud Run） | 友人 |
| **手動トリガー**（デモ用に企画バッチ起動） | `POST /api/trigger/planning`（Cloud Run） | 友人 |

> API化するのは「Firestore直書きでは危険・不可能」な操作（予約・OAuth・手動トリガー）だけ。ユーザー入力の保存（FB・initialProfile・favoriteAuthors）はセキュリティルールで保護したFirestore直書きで足り、Cloud Run APIを足さない＝工数の物理分離。

### 1-a. ベースパス・CORS（G1-7＝MTG 2026-06-05確定）

- **ベースパス**: API は単一 Cloud Run サービスに `/api/*` で集約。フロントは `NEXT_PUBLIC_API_BASE_URL` で注入する。
- **CORS許可オリジン**: App Hosting 本番ドメイン ＋ `localhost:3000`（dev）。
- **メソッド**: `GET` / `POST`。**ヘッダ**: `Authorization` / `Content-Type`。
- **cookie 不使用**（認証は Bearer トークンのみ＝§2）。

---

## 2. 認証モデル（全API共通）

- フロントは **Firebase Auth** でログイン（Googleアカウント）。
- API呼び出しは HTTPヘッダに **Firebase ID トークン**を載せる：`Authorization: Bearer <Firebase ID token>`。
- バックは Firebase Admin SDK で**トークン検証 → `uid` 取得**。`uid` をサーバ側でユーザー識別に使う（**クライアントが渡す userId は信用しない**＝なりすまし防止）。
- 失敗時：未検証トークン＝`401`、権限不一致＝`403`。

```
共通エラー形式
{ "error": { "code": "string", "message": "string" } }
```

| HTTP | code 例 | 意味 |
|---|---|---|
| 400 | `invalid_argument` | リクエスト不正（必須欠落・型違反） |
| 401 | `unauthenticated` | トークン無効・欠落 |
| 403 | `permission_denied` | 他ユーザー資源へのアクセス |
| 404 | `not_found` | 対象book/planが存在しない |
| 409 | `conflict` | 状態遷移が不正（例：既にreserved） |
| 500 | `internal` | サーバ内部エラー |

---

## 2-a. ユーザー登録フロー（初期プロフィール＋OAuth接続）

MVPのユーザー登録は以下の順で完結する。すべてFirestore直書き または既存のOAuth APIで対応するため、**新規のCloud Run APIは不要**。マルチユーザー前提（`ownerUid`/`uid` で分離）。

### フロー
1. **Firebase Auth でGoogleログイン**（§2の前提）。
2. **初期プロフィール入力**（フロントがFirestore直書き）：`users/{uid}.initialProfile` を create（未設定時のみ・`Firestoreセキュリティルール.md` §3）。スキップ可（その場合は `skipped:true` を保存）。
3. **OAuth接続**（既存 `GET /api/auth/google/start` → `callback`）：Drive/Calendar/Tasks の3スコープを同意取得。完了後サーバが `connectedSources` を更新。

### initialProfile スキーマ（`users/{uid}.initialProfile`）
```jsonc
{
  "industry": "食品・飲料",                 // ①業界（単一選択・必須）
  "jobType": "マーケティング・ブランド",     // ②職種（単一選択・必須）
  "position": "課長・マネージャー",          // ③役職（単一選択・必須）
  "recentInterests": ["新任マネジメント・チームづくり", "評価・フィードバック"],  // ④最近の関心（複数選択・最低1つ必須）
  "readingGenres": ["すぐ使える実践書・ハウツー", "事例・ストーリーで学ぶ"],  // ⑤読み口・形態の好み（複数選択／著者ペルソナのformat/voiceStyle生成・許容度初期値に活用）※キー名はreadingGenresで据え置き
  "createdAt": "ISO8601",
  "skipped": false                         // スキップ時 true（①〜⑤なしでもDrive観測で動く）
}
```

#### 入力形式・必須/任意（2026-06-03確定）
- ①業界 ②職種 ③役職：**単一選択（必須）**／④最近の関心：**複数選択・最低1つ必須**／⑤本のタイプ（読み口・形態）：**複数選択**。全体スキップは可（`skipped:true`）。

#### 選択肢（確定・正本＝`apps/web/src/data/profileOptions.ts`／`apps/mockup/...` は同内容のデザイン参照コピー・G1-11でフロント正本は `apps/web` に確定）
- **①業界**: 食品・飲料／日用品・化粧品（消費財）／製造・メーカー（その他）／小売・流通／IT・ソフトウェア／金融・保険／コンサル・専門サービス／商社／医療・製薬・ヘルスケア／建設・不動産／広告・メディア・エンタメ／公共・教育・非営利／その他
- **②職種**: マーケティング・ブランド／営業・セールス／企画・経営企画／商品開発・R&D／生産・製造・品質／人事・総務／経理・財務／情報システム・IT／コンサルタント／経営・役員／その他
- **③役職**: メンバー・担当／チームリーダー・主任／課長・マネージャー／部長・シニアマネージャー／本部長・事業部長／役員・経営層／個人事業・フリーランス
- **④最近の関心**（複数・最低1）: 新任マネジメント・チームづくり／メンバー育成・1on1／評価・フィードバック／リーダーシップ／戦略・事業計画／マーケティング・ブランディング／ロジカルシンキング・問題解決／数字・データ活用／業務効率化・生産性／AI・生成AIの活用／組織変革・カルチャー／キャリア・自己成長／プレゼン・伝える力／会議・ファシリテーション／モチベーション・メンタル／イノベーション・新規事業／顧客理解・CX／時間管理・段取り／交渉・調整
- **⑤本のタイプ（読み口・形態）**（複数）: 体系的な理論書でじっくり／すぐ使える実践書・ハウツー／事例・ストーリーで学ぶ／対談／インタビュー形式／図解・ビジュアル中心／物語・小説で楽しむ／ほぼ読まない

> **Firestore直書きの根拠**: バックエンド処理（LLM・外部API）が不要で、選択値をそのまま保存するだけ。セキュリティルールで保護した直書きで十分（Cloud Run APIを立てると友人工数を余分に消費）。

---

## 3. `POST /api/reserve`（予約＝後追い執筆の発火）

ユーザーが棚の1冊（著者版）を選び「予約」する。Firestoreの状態更新とPub/Sub発行を**1エンドポイントで原子的に**行う。**予約の原子性は Firestore transaction で担保（I-20＝MTG 2026-06-05確定）**＝「reserved+writing の冊数を読む→ <5 を確認→ `draft→reserved` 遷移」を1単位で実行し、レースで6冊目が通るのを防ぐ。

### Request
```jsonc
// Header: Authorization: Bearer <Firebase ID token>
{
  "bookId": "string"          // 予約する books/{bookId}
}
```

### 処理
1. トークン検証 → `uid`。
2. `books/{bookId}` を取得。存在しなければ `404`。
3. 所有者チェック（`book.ownerUid == uid`／§FIRESTORE_SECURITY）。不一致 `403`。
4. **以下4〜6を Firestore transaction で実行（I-20）**：
   - `status != "draft"` なら `409`（既に予約/執筆/公開済み）。
   - **予約上限チェック（★同時最大5冊・I-16解決）**: 当該ユーザーの `status in (reserved, writing)` の冊数を数え、**5冊以上なら `409`（`reservation_limit_exceeded`）**。単位＝**同時**（reserved+writing の合計）。本文Pro生成のコスト天井（MVPスコープ §5-2）。
   - `status: draft → reserved` に更新（条件確認と遷移を1単位で＝レースで6冊目を防ぐ）。
5. Pub/Sub トピック `book-writing` に `{ bookId }` を発行（→ モードB 本文編集ループ：編集長⇄著者 最高3R）。**WritingWorker は冪等＝status が writing/published ならスキップ（bookId基準・I-20）**。
6. 成功レスポンス。

### Response（200）
```jsonc
{
  "bookId": "string",
  "status": "reserved",
  "message": "予約しました。執筆を開始します。"
}
```

> 以降の `reserved→writing→published` はWritingWorkerが進め、**フロントはFirestore購読で受け取る**（APIのポーリング不要）。

---

## 3-a. お気に入り著者の保存／削除（Firestore直書き）

ユーザーが読書中／読了後に著者を保存する操作。バックエンド処理が不要なため Firestore 直書きで実装（§1方針）。**Cloud Run API不要**。

### 保存（追加）
```javascript
import { doc, updateDoc, arrayUnion } from "firebase/firestore";
await updateDoc(doc(db, "users", uid), {
  favoriteAuthors: arrayUnion({
    personaId: persona.personaId,
    name: persona.name,             // orphan防止のためコピー
    voiceStyle: persona.voiceStyle, // 文体軸（orphan防止のためコピー）
    format: persona.format,         // 文章形式（同上）
    savedAt: new Date().toISOString()
  })
});
```

### 削除（取り消し）
```javascript
import { arrayRemove } from "firebase/firestore";
await updateDoc(doc(db, "users", uid), { favoriteAuthors: arrayRemove(existingEntry) });
```

> **orphan防止（`Firestoreセキュリティルール.md` §5）**: personaId の参照先が ephemeral=true（都度生成）の場合、後で削除されると参照切れになる。**保存時に name/voiceStyle/format をコピーして持つ**ことで、ephemeralペルソナが消えても favoriteAuthors は壊れない。保存された著者は次回の企画生成（STEP3a）で混入候補として渡される（MVPは混入比率15%＝各枠15%の確率で採用）。

---

## 4. OAuth連携（Drive / Calendar / Tasks のトークン交換）

初回に観測3ソースへのアクセス同意を取り、リフレッシュトークンをサーバに保存する。スコープは `drive.file` / `calendar.readonly` / `tasks.readonly`（demo/README・テストモード）。

### 4-1. `GET /api/auth/google/start`
- Header: `Authorization: Bearer <Firebase ID token>`
- 処理：Google OAuth同意画面へのリダイレクトURLを生成（`state`にCSRF対策トークン、`access_type=offline`でrefresh_token取得、対象3スコープを要求）。
- Response（200）：`{ "authUrl": "https://accounts.google.com/o/oauth2/v2/auth?..." }`（フロントはこのURLへ遷移）。

### 4-2. `GET /api/auth/google/callback`
- Googleからのリダイレクト受け口（`?code=...&state=...`）。
- 処理：`state`検証 → 認可コードをトークンに交換 → **refresh_token を Secret Manager に保存**（G1-5＝Secret Managerで確定済・2026-06-03。生トークンを平文でFirestoreに置かない）→ `users/{uid}.connectedSources.{drive,calendar,tasks}.enabled=true` を更新。
- Response：フロントの設定完了画面へリダイレクト。

> **保存先＝Secret Manager で確定**（G1-5・`open-issues.md` 決着ログ／`infra/gcp-setup-log.md`）。MVPは個人＋テストモードのため当人のトークン1組で足りる。

---

## 5. `POST /api/trigger/planning`（手動トリガー・デモ用）

Cloud Scheduler（週3回・曜日別）と同じ企画バッチ（モードA／Cloud Run Job）を**手動で即時起動**する。デモ録画で「自律トリガーの成果」をその場で出すため。

### Request
```jsonc
// Header: Authorization: Bearer <Firebase ID token>
{
  "userId": "string?",          // 省略時はトークンの uid。MVPはデモユーザー固定で可
  "themeKind": "honmei",        // honmei | serendipity（省略時 honmei）。どの曜日runを再現するか
  "runAnalysis": false          // true なら STEP0観測+STEP1読者分析から走らせる（既定false=既存profile再利用）
}
```

### 処理
1. トークン検証 → `uid`。**許可uidリスト（デモ垢のみ）に制限＝コスト暴走防止（G1-6＝MTG 2026-06-05確定。将来レート制限）。許可外は `403`。**
2. Cloud Run Job「企画会議」を `themeKind`・`runAnalysis` を渡して起動（実行IDを払い出す）。
3. 即時 `202 Accepted` を返す（バッチ完了は待たない）。

### Response（202）
```jsonc
{ "runId": "string", "status": "accepted", "message": "企画バッチを起動しました" }
```

> 完了は数分かかる。フロントは `plans/`・`books/` のFirestore購読で「入荷」を検知する（ポーリング不要）。デモはこの遅延をカット編集で「翌朝」に飛ばす。

---

## 6. 未確定

> 本書に関する未確定論点は **`未決論点台帳.md` に集約**（関連: G1-4 ownerUid／I-5 initialProfile変更可否／I-7 favoriteAuthors上限／F-1 混入比率）。
> **✅ MTG 2026-06-05で確定済**: G1-3 予約の発火方式（明示API `POST /reserve`）／G1-5 OAuthトークン保存先（Secret Manager）／G1-6 手動トリガー認可（許可uidリスト＝デモ垢のみ）／G1-7 APIベースパス・CORS（§1-a）／I-20 予約の原子性（Firestore transaction・冪等ガード）。
