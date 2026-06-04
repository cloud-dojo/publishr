# Publishr Firestore セキュリティルール設計

> 📑 全体の目次・真実源マップは [目次.md](../目次.md)／未確定論点は [未決論点台帳.md](../計画/未決論点台帳.md)。

> **位置づけ**: `エージェントIO契約.md` §11が前提にする「ハイライト/FB/★はフロントからFirestore直書き（セキュリティルールで保護）」を**実際に保護するルール**を定義する。ルール無しの直書き設計は「誰でも読める・書ける」状態になり得るため、直書き方式の成立条件そのもの。
> **原典**: データモデル＝`技術アーキテクチャ.md` §3、連携方式＝`エージェントIO契約.md` §11、認証＝`API契約仕様.md` §2。
> **担当**: 友人（ルール実装・デプロイ）。鉄田は直書きするフィールド範囲を本書で握る。
> **ステータス**: 🟡 ドラフト（2026-06-02）。§2の `ownerUid` 追加は**データモデルへの小変更**＝友人MTGで合意してから反映。

---

## 0. 大前提：誰がルールに縛られるか

- **クライアント（フロント＝鉄田のWebアプリ）からのアクセスだけがルールに縛られる。**
- **バックエンド（Cloud Run上のエージェント・WritingWorker）は Firebase Admin SDK で動き、ルールを完全にバイパスする。** → 企画生成・著者版生成・状態遷移（draft→reserved→…）・profile更新は全てサーバ書き込みなので、ルール上は**クライアントの書き込みを原則禁止**にしてよい。
- つまりルールの仕事は：**「クライアントには、自分の資源を読む権利と、ごく限られたフィールドだけ書く権利を与える」**こと。

---

## 1. アクセス方針（コレクション別）

| コレクション | クライアント読み取り | クライアント書き込み | 備考 |
|---|---|---|---|
| `users/{uid}` | 本人のみ | **一部フィールドのみ可**（initialProfile・favoriteAuthors） | profile/connectedSources はサーバが書く |
| `users/{uid}.initialProfile` | 本人のみ | **初回create時のみ**（確定後はサーバ経由） | 登録フォームからの直書き |
| `users/{uid}.favoriteAuthors` | 本人のみ | **追加・削除のみ**（arrayUnion/Remove） | ワンクリック保存UI |
| `plans/{planId}` | 所有者のみ | 不可（企画はサーバ生成） | 入荷理由等の表示用に読む |
| `books/{bookId}` | 所有者のみ | **限定フィールドのみ**（FB/★） | status/title/body等は不可 |
| `books/{bookId}/highlights/{hid}` | 所有者のみ | **作成・自分の分の削除のみ** | ハイライトはサブコレクション |
| `personas/{personaId}` | 認証済みなら可（著者プロフィール表示） | 不可 | 内部資産（ephemeral含めサーバ書き込み）。読み取りのみ |

> **ハイライト・簡易FBはサブコレクション or 限定フィールドに分離する**のが安全。本文(bodyUrl)・タイトル・status をクライアントに書かせない（改竄・不正な状態遷移の防止＝予約は必ず `POST /api/reserve` 経由）。

---

## 2. 所有権モデル（ownerUid 方式・§3で確定済み）

`plans/` `books/` は **Firestore自動ID＋親子はフィールド**（`book.planId`等）で持ち、所有権判定のため **`ownerUid`（Firebase Auth uid）フィールドを持つ**（→ スキーマ定義の真実源は `技術アーキテクチャ.md` §3）。

- サーバ（モードA）が生成時に `ownerUid` を埋める。
- ルールは `resource.data.ownerUid == request.auth.uid` で所有権を判定。
- MVPは単一ユーザーだが、マルチユーザー前提インフラのため最初から組み込む。

> セキュリティルール固有の未確定（ownerUidフィールド方式 vs サブコレクションネスト等）は `未決論点台帳.md`（G1-4）に集約。本ルールは**ownerUidフィールド方式**で記述する。

---

## 3. セキュリティルール本文（ドラフト）

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // 共通ヘルパ
    function isSignedIn() {
      return request.auth != null;
    }
    function isOwner(uid) {
      return isSignedIn() && request.auth.uid == uid;
    }
    // 更新時に「許可フィールド以外が変更されていない」ことを保証
    function onlyChanged(allowedFields) {
      return request.resource.data.diff(resource.data).affectedKeys()
               .hasOnly(allowedFields);
    }

    // ── users：本人のみ読める ──
    // profile / connectedSources はサーバ（Admin）が書く。
    // initialProfile（初回のみ）と favoriteAuthors（ワンクリック保存）はクライアントが書く。
    match /users/{uid} {
      allow read: if isOwner(uid);

      // ドキュメント新規作成：本人が initialProfile のみを持って作成（登録フォーム）
      allow create: if isOwner(uid)
                    && request.resource.data.keys().hasOnly(['initialProfile']);

      // 更新：initialProfile（未設定時のみ）と favoriteAuthors のみ変更可
      allow update: if isOwner(uid)
                    && onlyChanged(['initialProfile', 'favoriteAuthors'])
                    // initialProfile を変えるのは、まだ存在しない初回のみ（確定後はサーバ経由）
                    && (!('initialProfile' in resource.data)
                        || !request.resource.data.diff(resource.data)
                              .affectedKeys().hasAny(['initialProfile']));
      allow delete: if false;
    }

    // ── plans：所有者のみ読める。生成はサーバのみ ──
    match /plans/{planId} {
      allow read:  if isSignedIn() && resource.data.ownerUid == request.auth.uid;
      allow write: if false;
    }

    // ── books：所有者のみ読める。クライアント書き込みはFB/★の限定フィールドのみ ──
    match /books/{bookId} {
      allow read:  if isSignedIn() && resource.data.ownerUid == request.auth.uid;

      // 新規作成・削除・全面更新はサーバのみ
      allow create, delete: if false;

      // 既存bookの「フィードバックだけ」をクライアントが更新可
      // status / title / bodyUrl / coverUrl / planId / ownerUid 等は変更不可
      allow update: if isSignedIn()
                    && resource.data.ownerUid == request.auth.uid
                    && onlyChanged(['feedback']);   // feedback={rating,wantsSequel,read%,dropped}

      // ── ハイライト（サブコレクション）──
      match /highlights/{hid} {
        allow read:   if isSignedIn()
                      && get(/databases/$(database)/documents/books/$(bookId))
                           .data.ownerUid == request.auth.uid;
        // 自分のbookに、自分のuidでハイライトを作成・削除できる
        allow create: if isSignedIn()
                      && request.resource.data.ownerUid == request.auth.uid
                      && get(/databases/$(database)/documents/books/$(bookId))
                           .data.ownerUid == request.auth.uid;
        allow delete: if isSignedIn()
                      && resource.data.ownerUid == request.auth.uid;
        allow update: if false;          // ハイライトは作る/消すのみ
      }
    }

    // ── personas：認証済みなら読める（著者プロフィール表示）。書き込みはサーバのみ ──
    // ※ ephemeral=true（都度生成）のペルソナもサーバ（Admin）が書く。クライアントは読むのみ。
    match /personas/{personaId} {
      allow read:  if isSignedIn();
      allow write: if false;
    }

    // ── それ以外は全拒否 ──
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

> ⚠️ `onlyChanged(['feedback'])` で許可フィールドを `feedback` に限定。読書ログ（read%/dropped）をクライアントが書くなら `feedback` 配下に入れる設計にして、トップレベルフィールドを直接書かせない。簡易FB・★・読了率はすべて `feedback` オブジェクトに集約すると、ルールが1行で済む。

---

## 4. 設計上の含意（フロント実装＝鉄田への指示）

- ハイライト保存：`books/{bookId}/highlights/{自動ID}` に `{ text, ownerUid, createdAt }` を**create**する（自分のuidを必ず入れる）。
- FB/★保存：`books/{bookId}` の **`feedback` フィールドだけ**を更新する（`{ rating, wantsSequel, readPercent, dropped }`）。status等は触らない。
- 予約：Firestore直書きでstatusを変えない。必ず `POST /api/reserve` を呼ぶ（`API契約仕様.md` §3）。
- 初期プロフィール保存：登録フォームから `users/{uid}` に `{ initialProfile: {...} }` を**create**する（初回のみ・既存時はUIでスキップ）。
- お気に入り著者保存：`users/{uid}.favoriteAuthors` を `arrayUnion({personaId, name, voiceStyle, format, savedAt})` で追記。ハートを外したら `arrayRemove`。personaId参照先が消えても壊れないよう name/voiceStyle/format をコピーして持つ（§5・persona は voiceStyle＋format に分割済）。
- 読み取り：棚・本詳細・本文メタは購読でOK（所有者なら読める）。

---

## 5. 未確定

> 本書に関する未確定論点は **`未決論点台帳.md` に集約**（関連: G1-4 ownerUid方式 vs ネスト／I-6 initialProfile書込制限の実装／I-8 favoriteAuthors参照方式／I-9 読書ログの置き場所／I-10 本文(GCS)保護／I-11 personas読み取り開放）。
