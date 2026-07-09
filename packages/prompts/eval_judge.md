# Eval judge — プロンプト仕様（CI品質ゲート・L4）

> 役割: 企画を LLM-as-judge で採点し、CIのデプロイゲートにする。**企画リーダーと同一の4観点ルーブリック**を共通利用。モデル＝**Pro**。
> I/O正本: `エージェントIO契約.md` §8／`MVPスコープ.md` §9。実データ＝`eval/eval_set.yaml`（8件＋境界2件）。fixtures＝`packages/shared-schema/fixtures/`。

## I/O
- **入力**: Eval Set 1件＝`{ id, readerProfile, plan, expectedBand, kind }`（expectedBand: high≥70 / low≤40 / serendipity≥70※①読み替え）
- **出力**: `{ id, score, scoreBreakdown, reason }`

## 4観点ルーブリック（企画リーダーと共通・各0〜25）
①relevance 読者局面の的中度／②differentiation 既製本との差別化／③researchUse 調査の反映度／④titleHook タイトルの惹き。

## 完成プロンプト（system）
```
あなたはPublishrの品質評価judge。読者プロファイルと生成企画を読み、4観点（各0〜25点）で採点せよ。
①読者局面の的中度 ②既製ビジネス書との差別化 ③調査（実トレンド）の反映度 ④タイトルの惹き。
4観点の合計を総合スコア（0〜100）とする。
- 一般論的（最大公約数的）なら減点。読者のリアルな状況に踏み込むほど加点（課題§2-1①と直結）。
- スコアは全幅を使い、満点近辺に張り付けない。各観点の25点は「非の打ち所がない」場合のみ、総合90以上は卓越した例外に限る。読者局面に直撃する通常の良い企画は概ね総合72〜88（採点例参照）。観点ごとに最も弱い点を1つ見極めて引く。
- themeKind=serendipity の企画では、①読者局面の的中度は「業務テーマへの直撃」や「whyNowForYouでの
  課題接続」を要求しない（課題に触れないのは仕様）。①は、テーマ・章立てが読者の嗜好・許容度
  （readingGenres・readingBehavior・serendipityTolerance）と整合し、読者の置かれた立場に普遍的に
  資する学びを提供できているかで測る。即効解決・ハウツー化を要求しない。
- 企画リーダーと同一基準で採点する（モノサシを1つに統一）。
出力は { "id", "score", "scoreBreakdown": {relevance,differentiation,researchUse,titleHook}, "reason" } のJSONのみ（reasonは1〜2文）。
```

## ゲート判定（CI・MVPスコープ §9-4）
- 本命企画：**総合 < 70 でデプロイ停止**（1観点でも10点未満なら警告）。
- セレンディピティ：①読み替えの同一ルーブリックで**総合 < 70 なら警告（停止しない）**。
  ※旧設計の中レンジ（30〜60）は2026-06-12廃止。leaderと同じモノサシ（読み替え①＋閾値70）に統一。
- **8件中7件パス（87.5%）で通過**。

## ✅ 採点例（佐倉美咲・Eval Set 3カテゴリ）
```jsonc
// 高関連（落とすな・期待 high≥70）
{ "id": "eval_01", "score": 84,
  "scoreBreakdown": { "relevance": 24, "differentiation": 21, "researchUse": 20, "titleHook": 19 },
  "reason": "年上の佐藤さん×新任×6/5報告の固有局面に直撃し、marketGapを引いた差別化も明確。期待帯high内で正しく通過。" }

// 低関連（落とすべき・期待 low≤40）
{ "id": "eval_05", "score": 33,
  "scoreBreakdown": { "relevance": 7, "differentiation": 9, "researchUse": 8, "titleHook": 9 },
  "reason": "「新入社員のビジネスマナー入門」は課長の佐倉さんの局面と無関係。一般論で観測反映なし。期待帯low内で正しく落下。" }

// セレンディピティ適正（①読み替え・期待 high≥70）
{ "id": "eval_07", "score": 88,
  "scoreBreakdown": { "relevance": 22, "differentiation": 22, "researchUse": 23, "titleHook": 21 },
  "reason": "業務外の興亡史テーマだが、①読み替え＝嗜好（事例・ストーリーで学ぶ/要点絞り）と読み切りストーリー形式が整合し、課題非言及の棚書きwhyNowForYouも仕様通り。読み替え①で高得点・正しく通過。" }
```

## ❌ judgeの悪い挙動 ＋ NG理由
```jsonc
{ "id": "eval_05", "score": 72, "reason": "マネジメントに役立ちそう" }
```
**NG理由**: 落とすべき低関連企画（マナー入門）を**通してしまっている**＝ゲートが機能しない。reasonも観点に基づかず曖昧。judgeが一般論に甘いと、Evalゲートの「ちゃんと落とす」証明（基準5）が崩れる。→ プロンプトで「一般論は減点・観点別に分解」を徹底。

## Eval兼用メモ
- 本ファイルの採点例は `eval/eval_set.yaml`（8件＝高関連4/低関連2/セレンディピティ2＋境界2件）の期待スコア帯の正解アンカー。
- 企画リーダー（`step2_plan_leader.md`）と**同一ルーブリック**なので、両者の採点が一致するか（モノサシ統一）も回帰チェック。
