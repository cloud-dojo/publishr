# Publishr Langfuse トレース仕様（ドラフト）

> 📑 全体の目次は [正本マップ](../README.md)／未決論点は [open-issues.md](../planning/open-issues.md)（B1）。
> **位置づけ**: 「何を・どの単位でLangfuseに残すか」を定義する。狙いは **基準1（AIエージェントの必然性）の証跡を可視化**すること＝「調査サブが外部実データを取る」「企画リーダーがスコアで差し戻す」「編集長が著者を差し戻す」が**実行時に本当に起きている**ことをトレースで示す。Observability L4（継続評価）の土台。
> **担当**: 計装実装＝友人（W4）。本書（何を残すか）＝鉄田ドラフト→友人MTG（2026-06-05）で「何を残すか」は合意。実装方式（OTel/SDK直）のみ先送り（G1-17）。
> **ステータス**: 🟡 ドラフト（2026-06-03）。**実装方式（OTel経由 or Langfuse SDK直）は MTG 2026-06-05で判断不可＝先送り（今後W1疎通以降に検証しながら確定・G1-17）**。3シグナル設計（何を残すか）自体は維持。span名・属性キーはW1のADK/Langfuse疎通で実APIに合わせて確定。

---

## 0. 原則
- **trace = 1実行単位**（モードA企画run＝1 trace／モードB執筆＝1 trace／Eval CI 1回＝1 trace）。
- **span = エージェント1呼び出し**（ネストで階層を表現）。
- 必然性の3シグナル（①調査grounding ②企画スコアループ ③編集ループ）を**属性（metadata）として明示的に残す**＝後から「演出でない」ことを数字で見せられる。
- PII配慮：userIdはハッシュ化 or デモ固定ID。本文全文はGCS参照（trace本体に焼かない）。

---

## 1. モードA（企画run）trace 構成
```
trace: planning_run  (attrs: runId, userId, themeKind, dayOfWeek, env)
├─ span STEP0 observation (tool)   attrs: driveFiles数, calendarEvents数(±14日), tasks数
├─ span STEP1 reader_analyst (Pro) attrs: model, profileLayersUpdated=[currentWork,readingBehavior], evidenceCount
├─ span STEP2 planning_loop        attrs: maxRounds=3, finalRound, finalScore, approved(bool)
│   ├─ span research_subs (Flash)  ★①grounding証跡
│   │     attrs: subMarket.queries[], subMarket.retrievedUrls[], subMarket.marketGap,
│   │            subThemeInsight.queries[], subThemeInsight.retrievedUrls[]
│   ├─ span plan_owner (Pro・roundごと) attrs: round, proposalId
│   └─ span plan_leader (Pro・roundごと) ★②企画スコアループ証跡
│         attrs: round, score, scoreBreakdown{relevance,differentiation,researchUse,titleHook},
│                belowFloor, decision(approve|revise), rejectionFeedback(revise時)
├─ span STEP3 casting (Pro)        attrs: personaCount=5, voiceStyleSet[], formatSet[], fromFavoriteCount
├─ span STEP4 preview_edit_loop (著者5人)  ★③編集ループ証跡(プレビュー)
│   └─ per author: span author_preview (Pro) → span editor_preview (Pro)
│         attrs: bookId, editRound, editorScore, scoreBreakdown{rawInsight,personaForward,catchiness}, decision
└─ span STEP5 cover (Flash+Imagen) attrs: bookId, imagenCalled(bool・dev時false)
```

## 2. モードB（本文執筆）trace 構成
```
trace: writing_run  (attrs: bookId, userId, env, reservationCountAtStart)
└─ span body_edit_loop  ★③編集ループ証跡(本文)  attrs: maxRounds=3, editRounds, finalScore
    └─ per round: span author_body (Pro) → span editor_body (Pro)
          attrs: round, score, scoreBreakdown{coherence,hook,relevance,personaConsistency,actionability},
                 weakChapters[], decision(approve|revise)
```

## 3. Eval（CI品質ゲート）trace 構成
```
trace: eval_gate  (attrs: commitSha, env)
└─ per case (8件): span eval_judge (Pro)
      attrs: id, kind(high/low/serendipity), score(0-100), scoreBreakdown(4観点),
             expectedBand, pass(bool), reason
   trace末: gateResult{ passCount, total=8, passed(>=7), honmeiAllPassed }
```

> **②採用メモ（2026-06-05）**: `eval_judge` の score/scoreBreakdown/reason は **Vertex AI Gen AI Evaluation Service**（`vertexai.evaluation`）が算出した結果を Langfuse に記録する（自作judge実行を置換）。trace/span構成・属性キーは不変。

## 4. 必然性ダッシュボード（Langfuseで見せる3点）
| 見せたいもの | 使う属性 | 基準 |
|---|---|---|
| 調査が外部実データを取った | research_subs の retrievedUrls[]・queries[]・marketGap | 1 |
| 企画を採点して差し戻した | plan_leader の score推移・rejectionFeedback・finalRound>1 の事例 | 1 |
| 著者を採点して差し戻した | editor_preview/editor_body の score推移・weakChapters・editRounds>1 | 1 |
| 品質ゲートが機能 | eval_gate の passCount・low帯を落とした事例 | 5 |
| コスト/レイテンシ | 各spanの token/cost/latency（Langfuse標準） | 5（数字で語る） |

## 5. 未確定（W1疎通以降で確定）
- **ADKのトレース連携方式（OpenTelemetry経由か Langfuse SDK直か）＝MTG 2026-06-05で判断不可・先送り（G1-17）**。現時点では決めず、今後W1疎通以降に検証しながら確定する。
- grounding の retrievedUrls をADK/Vertexのどのフィールドから取れるか（取れない場合は調査サブ出力の `findings[].source` を代替に）。
- trace/span命名規約の最終化・属性キーのスネーク/キャメル統一。
- コスト属性の取得（Vertex課金 × Langfuse cost フィールドのマッピング）。
