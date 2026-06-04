# Publishr ADKオーケストレーション設計（制御フロー）

> 📑 全体の目次・真実源マップは [目次.md](../目次.md)／未確定論点は [未決論点台帳.md](../計画/未決論点台帳.md)。

> **位置づけ**: 「各エージェントが何を受け取り・何を返すか」を定めた `エージェントIO契約.md` に対し、本書は **「それらをどう繋いで・どう回すか（制御フロー／トポロジ）」** を定める。最大の技術リスク＝**W1関門（ADK疎通）**と**STEP2のスコア閾値 差し戻しループ**の実装可否を、着手前に図にして潰すための設計書。
> **原典との関係**: パイプライン＝`技術アーキテクチャ.md` §1、I/O＝`エージェントIO契約.md` §1-7、必然性論＝同 §7／構想 §6-2d。本書は新しい仕様判断はせず、既存確定事項を**実行可能な制御フロー**に翻訳する。
> **担当**: 友人（エージェント基盤）。鉄田はドラフトを用意し友人MTGで握る。
> **ステータス**: 🟡 ドラフト（2026-06-02）。⚠️ ADKの具体API名（クラス・メソッド）は§9のとおり**W1 Hello Worldで要実証**。本書は制御フローの論理設計を確定し、API対応はW1で確認する。

---

## 0. 設計の前提（不変）

- **エージェント＝判断する所だけ。** データを動かすだけの処理はツール（バッチ）でエージェントにしない（構想 §6-2d 設計規律）。
- **決定論的な順序制御はワークフローで、判断はLLMで。** STEP間の進行は固定（Sequential）、各STEP内の「割れ方・採否」だけをLLMに委ねる。
- **必然性の核は2つの評価ループ**＝①STEP2「調査サブ（Google検索）→担当者が立案→リーダーがスコア化し差し戻す（最高3R）」＋②編集ループ「編集長が著者の成果を採点して差し戻す（STEP4プレビュー1R／モードB本文 最高3R）」が**実行時に本当に起きる**こと。図にできない＝演出に見えるリスク（基準1）。

---

## 1. 実行形態（2モード）

| モード | 起動 | 実行基盤 | 役割 |
|---|---|---|---|
| **モードA（自律企画）** | Cloud Scheduler（週3回・曜日別ジョブ）→ Cloud Run **Job** | バッチ（最後まで一気に走る） | 土/水=本命、日=セレンディピティ。各runで STEP2→3→4 を直列実行し棚に5冊を `draft` で並べる（STEP0/1は土朝のみ・水/日は土朝profile再利用）。週で本命10冊＋セレンディピティ5冊＝15冊 |
| **モードB（後追い執筆）** | ユーザー選択 → `status:draft→reserved` → Pub/Sub → Cloud Run **Service** | 非同期ワーカー | 予約された本（★最大同時5冊）を編集ループ（編集長⇄著者・最高3R）で本文を階層生成 |

> モードAは「人間の応答待ち」が無い純バッチ。**STEP3で人間が選ぶのは別トリガー（モードB）**＝モードAはSTEP4まで一気に完走する。ここを混同しない（モードA内でユーザー選択を待たない）。
> **曜日別ジョブ**: 同一の Cloud Run Job を起動時パラメータ `themeKind`（honmei|serendipity）と「STEP0/1を走らせるか」のフラグで分岐させる。土=観測+分析+本命企画、水=本命企画のみ、日=セレンディピティ企画のみ。

---

## 2. エージェント木（モードA 全体）

ADKのワークフローエージェント（直列／並列／ループ）と LLMエージェントを入れ子にして構成する。

```
RootSequential（モードA・Cloud Run Job のエントリ／起動時に themeKind と STEP0/1実行フラグを受ける）
│
├─ [STEP0] ObservationTool（ツール・非エージェント／土朝のみ実行）
│      Drive/Calendar/Tasks 取得＋テキスト抽出 → state["observation"]
│
├─ [STEP1] ReaderAnalystAgent（LlmAgent・Flash／土朝のみ実行・週1回）
│      in: state["observation"] (+前回 profile + initialProfile)
│      out: state["readerProfile"]（水/日runは Firestore の profile を読んで state に載せ直す）
│
├─ [STEP2] PlanningLoop（LoopAgent・max_iterations=3）★必然性の本丸＝3階層
│   │   各ラウンドで以下を順に実行：
│   ├─ SubParallel（ParallelAgent・初回ラウンドのみ／担当者の配下／調査3観点）
│   │    ├ ReaderContextSubAgent（LlmAgent・Flash）→ state["subReaderContext"]（A 読者局面）
│   │    ├ MarketSubAgent（LlmAgent・Flash・Google検索grounding）→ state["subMarket"]（B 市場・競合）
│   │    └ ThemeInsightSubAgent（LlmAgent・Flash・Google検索grounding）→ state["subThemeInsight"]（C テーマ知見）
│   ├─ PlanOwnerAgent（LlmAgent・Pro）＝企画担当者・立案（調査3観点を統合し企画書8項目を作る）
│   │         in: readerProfile ＋ themeKind ＋ 調査3観点 (+ round>1は rejectionFeedback)
│   │         out: state["planDraft"]（PlanProposal・8項目）
│   └─ PlanLeaderAgent（LlmAgent・Pro）＝企画リーダー・スコアゲート
│             in: state["planDraft"] ＋ readerProfile ＋ themeKind
│             out: state["leaderVerdict"]（score / decision）
│             ・approve（score≥閾値）→ state["approvedPlan"] を確定し escalate（脱出）
│             ・revise → state["rejectionFeedback"] を書いて次ラウンドへ（担当者が練り直す）
│
├─ [STEP3] PersonaGeneratorAgent（LlmAgent・Pro・1コールで5人を都度生成＝キャスティング編集者）
│      in: state["approvedPlan"] ＋ readerProfile ＋ favoriteAuthors（任意）
│      out: state["generatedPersonaSet"]（架空著者5人）
│      ── 生成ペルソナを personas/{personaId}（ephemeral=true）に保存。著者を“揃える”役（書かせない）──
│
├─ [STEP4] PreviewEditLoop ×5著者（各著者ごとに LoopAgent・max_iterations=2＝初稿＋1R改稿）★新設
│      ├ AuthorEngineAgent（Pro・3a生成ペルソナを着せ替え）→「はじめに＋核心メッセージ＋アジェンダ」= BookDraft
│      └ EditorAgent（編集長・Pro）：プレビュー3観点で採点 → approve（脱出）/ revise（editorFeedback書いて1Rのみ再執筆）
│      out: books/{bookId} に status=draft で保存（Firestore）×5
│
└─ [STEP5] CoverParallel（軽エージェント＋Imagen）
       装丁方針(Flash) → Imagen生成 → books/{bookId}.coverUrl 更新
```

> **本命/セレンディピティは同一構造**: 上記のSTEP2-4をそのまま使い回し、起動時の `themeKind` だけを切り替える（本命=土/水、セレンディピティ=日）。専任エージェントを別途持たず、PlanOwnerAgent のプロンプトが themeKind で振る舞いを変える。
> **サブの再実行**: SubParallel は初回ラウンドのみ起動が既定。差し戻し（revise）時は担当者が既存の sub成果を元に練り直す（サブ再実行はしない）。W1では「担当者1体＋リーダー1体＋サブ1体」の最小構成で疎通を確認し、サブの拡充は後付けで可。

---

## 3. STEP2 制御フロー詳細（スコア閾値の差し戻しループ）★本書の核心

`エージェントIO契約.md` §4-2a の「max_rounds=3・スコア閾値ループ」を制御フローに落とす。

```
round = 1
┌──────────────────────────────────────────────────┐
│ LoopAgent（max_iterations = 3）                    │
│                                                   │
│  1) 調査サブ3観点（初回のみ）→ 企画担当者が立案       │
│     - A読者局面 / B市場競合(Google検索) / Cテーマ知見(Google検索)│
│     - round1: readerProfile ＋ themeKind ＋ sub成果  │
│     - round>1: ＋ rejectionFeedback（前Rのリーダー指摘）│
│       担当者は既存sub成果を元に planDraft を練り直す   │
│                                                   │
│  2) 企画リーダー（Pro）がスコア化（4観点・各0〜25）   │
│     ①的中度 ②差別化 ③調査反映 ④タイトル惹き         │
│           → 総合 score（0〜100）                     │
│                                                   │
│     score ≥ 閾値70 かつ 全観点≥10 → approve         │
│        approvedPlan を確定し escalate（脱出）        │
│     score < 閾値 → decision=revise                 │
│        rejectionFeedback を state に書く            │
│        round == 3 なら最良案を承認（強制approve）     │
│        （4回目はしない＝コスト暴走防止）              │
└──────────────────────────────────────────────────┘
```

**実装上の要点**
- **ループ脱出の手段**: PlanLeaderAgent が `approve`（score≥閾値）と判断したら、ADKの **`escalate`（停止シグナル）** を立ててLoopを抜ける。`revise` なら立てない＝次イテレーションへ。
- **3ラウンド目の強制採用**: LoopAgent の `max_iterations=3` で3回目終了時に自動で抜けるが、**3回目のリーダーには「今回は最良案を必ず承認せよ（revise禁止）」をプロンプトで指示**し、空手で抜けないようにする。
- **状態の引き継ぎ**: `rejectionFeedback` は session state 経由。担当者（PlanOwnerAgent）のプロンプトは「state に rejectionFeedback があれば、指摘された弱い観点を最優先で直して企画を練り直せ」を含む（`エージェントIO契約.md` §4-2b プロンプト骨子）。
- **演出しない**: 「必ず1回差し戻す」ような細工はしない。スコアが閾値を超えれば1ラウンドで承認されてよい。仕組みとして閾値ループを持つことが目的（デモは別途録画）。
- **Langfuse**: 「スコア化→閾値未満で差し戻し→再提出」の遷移（スコアとラウンド数）を1トレースに残す＝基準1の生命線（MVPスコープ §5-2）。調査サブの検索クエリ・取得ソースもトレースに残す。

---

## 4. セッション状態（state）キー設計

ADKの session state（エージェント間で共有する辞書）に持たせるキー。型は `エージェントIO契約.md` のスキーマに準拠。

| キー | 産む工程 | 消費する工程 | 備考 |
|---|---|---|---|
| `observation` | STEP0（土朝のみ） | STEP1 | ObservationBundle |
| `readerProfile` | STEP1（土朝のみ・週1・Pro） | STEP2全体・STEP3・STEP4 | ReaderProfile（**3層**：base保持／currentWork・readingBehavior分析）。Firestore `users/{uid}.profile` に保存。水/日runはFirestoreから読み込む |
| `favoriteAuthors` | STEP起動時（Firestoreから取得） | STEP3a | users/{uid}.favoriteAuthors[]。初回は空配列 |
| `subReaderContext` / `subMarket` / `subThemeInsight` | STEP2 調査サブ3観点（初回R） | PlanOwnerAgent | A読者局面・B市場競合(Google検索)・Cテーマ知見(Google検索)の成果 |
| `planDraft` | PlanOwnerAgent | PlanLeaderAgent | PlanProposal（8項目・ラウンドごとに上書き） |
| `rejectionFeedback` | PlanLeaderAgent（revise時） | PlanOwnerAgent（次round） | 初期null。企画差し戻しループの燃料 |
| `leaderVerdict` | PlanLeaderAgent | （ループ制御） | score / decision / scoreBreakdown |
| `approvedPlan` | PlanLeaderAgent（approve時） | STEP3・STEP4 | ApprovedPlan。Firestore `plans/` に score/rounds/themeKind 付きで保存 |
| `generatedPersonaSet` | STEP3 キャスティング | STEP4 | 架空著者5人。personas/ に ephemeral=true で保存 |
| `editorFeedback` | EditorAgent（revise時・STEP4/モードB） | AuthorEngineAgent（次round） | 編集長の差し戻し指示。プレビュー編集ループ／本文編集ループの燃料 |
| `editorVerdict` | EditorAgent | （編集ループ制御） | score / decision（プレビュー3観点 or 本文ルーブリック） |
| （bookDraft×5） | STEP4（編集ループ後） | STEP5 | Firestore `books/` に直接保存（stateには要約のみ） |

> **大きい中間生成物（本文・抽出テキスト）はstateに溜めない。** Firestore/GCSを正本にし、stateには参照キー・要約だけを置く（コンテキスト肥大・コスト対策／`エージェントIO契約.md` §2注）。

---

## 5. モデル割当（`エージェントIO契約.md` §9と一致）

> 方針＝ハイブリッド（`エージェントIO契約.md` §9と一致）。

| エージェント | モデル | 理由 |
|---|---|---|
| ReaderAnalyst | **Pro** | 全工程の起点＝品質カスケード。3層Profile（base保持／currentWork・readingBehavior分析）。週1回（土朝） |
| 調査サブ3観点（読者局面/市場競合/テーマ知見） | Flash（B・Cは検索grounding） | 外部実データ取得・抽出寄り |
| PlanOwner（企画担当者・立案） | **Pro** | 調査3観点を統合し企画書8項目を練る |
| **PlanLeader（企画リーダー・スコアゲート）** | **Pro** | 最も判断が重い（スコア化＋閾値での差し戻し） |
| PersonaGenerator（キャスティング編集者・都度生成） | **Pro**（1コール） | 人格設計。架空ペルソナ5人を生成 |
| AuthorEngine（プレビュー／本文） | **Pro**（プレビューはFlash可） | 選択を左右／読者が読む成果物 |
| **Editor（編集長・プレビュー採点／本文採点）** | **Pro** | 3観点/本文ルーブリックでの採点・差し戻し |
| 装丁方針 | Flash＋Imagen | 方針＋生成 |
| モードB本文（著者＋編集長） | **Pro** | 予約制＋上限同時5冊で限られた冊数のみ＝最高品質を集中投下 |

---

## 6. モードB（後追い執筆）の制御フロー

```
Pub/Subメッセージ（bookId）受信　※予約上限同時5冊（reserve APIでチェック済）
   ▼
WritingWorker（Cloud Run Service）＝本文編集ループ（編集長 ⇄ 著者・最高3R）
   1) Firestoreから BookDraft / persona / approvedPlan / readerProfile を読む
   2) status: reserved → writing に更新
   3) BodyEditLoop（LoopAgent・max_iterations=3）：
        ├ AuthorEngineAgent（Pro）：アウトライン→章ごと本文（前章要約で一貫性）／2R目以降は editorFeedback の弱い章のみ改稿
        └ EditorAgent（編集長・Pro）：本文ルーブリック（I-12）で採点 → approve（脱出）/ revise（editorFeedback書いて再ループ）
   4) 通し校正（Pro）→ 本文MDをGCS保存
   5) books/{bookId}.bodyUrl 更新、status: writing → published（editRounds を記録）
```

- **改稿の範囲**: 全文を毎ラウンド再生成しない。**編集長が指摘した弱い章のみ**改稿（コスト抑制・`エージェントIO契約.md` §7）。
- **冪等性**: Pub/Subは再配信があり得る。`status==writing|published` のbookには再実行をスキップ（簡易ガード）。本格的な冪等キーはMVPでは不要（`エージェントIO契約.md` §10-3）。
- **タイムアウト**: 約100ページ生成＋編集ループは長い。Cloud Run Service のタイムアウト上限に注意（章ごとに分割保存し、途中失敗からの再開を可能にしておくと安全）。

---

## 7. W1最小疎通への落とし込み（最大リスクの潰し方）

W1関門「**担当者が立案し、リーダーがスコアで突き返す**が動く」を、本設計の**最小サブセット**として定義する：

```
MiniLoop（LoopAgent・max_iterations=3）
  ├ SubAgent（Flash・調査サブ1体＝Google検索grounding）→ state["subResearch"]（初回のみ）
  ├ OwnerAgent（Flash・固定）：sub成果(+feedback)を統合して planDraft を作る
  └ LeaderAgent（Pro or Flash）：planDraft をスコア化
       score≥閾値 → escalate / score<閾値 → rejectionFeedback書いて再ループ
```

- ここで確認すべきこと（W1のDoD）：
  1. SubAgent が **Google検索grounding** で外部データを取って返す（ツール使用が動く）。
  2. OwnerAgent が sub成果を読んで planDraft を作る。
  3. LeaderAgent が planDraft を読んで **score付きの採否を返す**。
  4. score<閾値 のとき **再ループが回り**、Owner が rejectionFeedback を受けて作り直す。
  5. score≥閾値 で **ループを抜ける**（escalate が効く）。
- これが動けば、STEP2本体は「サブを3体に増やす・ルーブリック精緻化・themeKind分岐」の拡張で済む＝**最大リスクはW1で構造的に潰れる**。

---

## 8. フォールバック（ADKでループ制御が詰まった場合）

- ADKの LoopAgent/escalate で「スコア閾値の差し戻し（revise→練り直し）」がうまく組めない場合、**STEP2だけ LangGraph に逃がす**（`技術アーキテクチャ.md` R1）。LangGraphは条件分岐・ループ・状態を明示的なグラフで書けるため、スコア閾値ループの制御が素直。
- 判断はW1で早期に行う（詰まったら粘らずLangGraphへ）。STEP0/1/3/4はADKのSequential/Parallelで十分なので、ハイブリッド（大半ADK＋STEP2のみLangGraph）も可。

---

## 9. 未確定・要検証

> 本書に関する未確定論点は **`未決論点台帳.md` に集約**（関連: 「W1 Hello Worldで実証するADK技術論点」の全項目／I-1 スコア閾値／I-2 ephemeral削除／I-3 ペルソナ保存タイミング）。
> ⚠️ ADK実APIに依存する項目は**記憶で断定せず**W1のHello Worldで実証する（スキル `google-agents-cli-adk-code` 参照）。詰まった項目は §8 フォールバックで吸収。
