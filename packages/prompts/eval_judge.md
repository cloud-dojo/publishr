# Eval judge — プロンプト仕様（CI品質ゲート・L4）

> 役割: 企画を LLM-as-judge で採点し、CIのデプロイゲートにする。**企画リーダーと同一の4観点ルーブリック**を共通利用。モデル＝**Pro**。
> I/O正本: `エージェントIO契約.md` §8／`MVPスコープ.md` §9。実データ＝`デモ素材/fixtures/eval_set.json`（8件）。

## I/O
- **入力**: Eval Set 1件＝`{ id, readerProfile, plan, expectedBand, kind }`（expectedBand: high≥70 / low≤40 / serendipity 30〜60）
- **出力**: `{ id, score, scoreBreakdown, reason }`

## 4観点ルーブリック（企画リーダーと共通・各0〜25）
①relevance 読者局面の的中度／②differentiation 既製本との差別化／③researchUse 調査の反映度／④titleHook タイトルの惹き。

## 完成プロンプト（system）
```
あなたはPublishrの品質評価judge。読者プロファイルと生成企画を読み、4観点（各0〜25点）で採点せよ。
①読者局面の的中度 ②既製ビジネス書との差別化 ③調査（実トレンド）の反映度 ④タイトルの惹き。
4観点の合計を総合スコア（0〜100）とする。
- 一般論的（最大公約数的）なら減点。読者のリアルな状況に踏み込むほど加点（課題§2-1①と直結）。
- 企画リーダーと同一基準で採点する（モノサシを1つに統一）。
出力は { "id", "score", "scoreBreakdown": {relevance,differentiation,researchUse,titleHook}, "reason" } のJSONのみ（reasonは1〜2文）。
```

## ゲート判定（CI・MVPスコープ §9-4）
- 本命企画：**総合 < 70 でデプロイ停止**（1観点でも10点未満なら警告）。
- セレンディピティ：中レンジ（30〜60目安）のレンジ外なら警告（停止しない）。
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

// セレンディピティ適正（中レンジ・期待 30〜60）
{ "id": "eval_07", "score": 48,
  "scoreBreakdown": { "relevance": 12, "differentiation": 14, "researchUse": 11, "titleHook": 11 },
  "reason": "「リーダーのための東洋哲学入門」は直近の困りごとから一歩遠いが、関心の隣接として刺さりうる。中レンジで適正。" }
```

## ❌ judgeの悪い挙動 ＋ NG理由
```jsonc
{ "id": "eval_05", "score": 72, "reason": "マネジメントに役立ちそう" }
```
**NG理由**: 落とすべき低関連企画（マナー入門）を**通してしまっている**＝ゲートが機能しない。reasonも観点に基づかず曖昧。judgeが一般論に甘いと、Evalゲートの「ちゃんと落とす」証明（基準5）が崩れる。→ プロンプトで「一般論は減点・観点別に分解」を徹底。

## Eval兼用メモ
- 本ファイルの採点例は `eval_set.json`（8件＝高関連4/低関連2/セレンディピティ2）の期待スコア帯の正解アンカー。
- 企画リーダー（`step2_plan_leader.md`）と**同一ルーブリック**なので、両者の採点が一致するか（モノサシ統一）も回帰チェック。
