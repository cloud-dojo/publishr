# 価値観スコアカード（編集判断の正本）

> オーナー（鉄田）が STEP1–5 プロンプト出力を**自分の編集者としての価値観**で採点するための正本。
> 運用設計の全体像は計画ファイル（Human-in-the-Loop 最終プロンプト品質レビュー運用）を参照。

## 1. これは何か / どこに効くか

レビューは4層に分かれる。本スコアカードは **層2（人間・価値観）** の採点基準であり、層3（実UI体験）の content-in-context 判断にも流用する。

| 層 | 担い手 | 道具 | 本書の関与 |
|---|---|---|---|
| 1. 自動・決定的 | `scripts/smoke_discipline.py` / `verify-prompts` | 規律違反の機械検出 | **対象外**（ここで緑のものを二度見しない） |
| 2. 人間・価値観 | オーナー | **本スコアカード** ＋ ギャラリー | 採点の本体 |
| 3. 実UI体験 | オーナー | 実UI（環境B/C） | ⑦⑨を文脈で再確認 |
| 4. 最終ゲート | Gemini/Vertex/Imagen | `run_aistudio_batch` 等 | 書誌・grounding・実描画（採点しない） |

**原則**：自動層（層1）が決定的に潰せる規律（schema汚染・採点自己矛盾・approvedPlan無改変・role越境・感情創作・few-shot汚染・員数/2軸・棚書き文法）は**ここで採点しない**。人間の時間は「自動では測れない価値」に集中する。

## 2. 採点スケール

**4段階：◎=3 / ○=2 / △=1 / ✗=0**（編集判断は連続値より質的判断が速く一貫する）。

- **◎** 期待を超える。出荷したい。
- **○** 合格。出せる水準。
- **△** 不足。要改稿。
- **✗** 不合格。一般論・空疎・規律外。

## 3. few-shot 汚染を踏まえた読み方（重要）

`u_sakura（佐倉）` は STEP1/2/3/4・`eval_judge`・`README` の few-shot に固有名・設定が深く埋め込まれている（STEP1には「佐倉美咲との実テストで92点」と明記）。
→ **S-H（u_sakura×honmei）が良く見えるのは暗記の可能性**。S-H は「これだけ汚染してこの程度か」の**上限（best case）参照**として読む。
→ **価値観判定の本丸は M-H（u_mita）と N-H（クリーン新規ペルソナ）**。見たことのない読者で良ければ本物。N-H で凡庸化したら過剰適合を発見できている（＝レビューが機能している証拠）。

## 4. ディメンション詳細（①〜⑩）

①〜④は `eval/eval_set.yaml` の4観点（relevance / differentiation / researchUse / titleHook）と1対1。⑤〜⑩は本書で追加する編集価値観。
各行の「自動の参考値」は `smoke_discipline.py` の metric。**参考値であり緑/赤の自動判定はしない**（特に人間必須 ①④⑥⑩）。

### ① 局面的中（脱・一般論） — STEP2 ／ eval: relevance
読者の固有局面（役職・組織規模・業界・currentWork）にどれだけリアルに踏み込めているか。
- ◎ 固有局面に直撃し、本人が言語化していない痛みまで先回りして当てる
- ○ 固有局面に当たっている
- △ 浅い／固有局面の代理語はあるが中身が空疎
- ✗ 一般論・最大公約数（誰にでも当てはまる）
- 自動の参考値：`_RELEVANCE_KW` 密度・感情語創作フラグ

### ② 差別化の本物性 — STEP2 ／ eval: differentiation
既製本が「構造的に出せない」固有局面への差分を本当に突いているか。
- ◎ 市販本が構造的に埋められない局面を突き、marketGap が実在
- ○ 差別化が明確
- △ 弱い／marketGap が曖昧
- ✗ 「特になし」級・marketGap の捏造
- 自動の参考値：`marketGapCitation`・diff↔marketGap 語彙重複

### ③ 調査が企画に生きる — STEP2 ／ eval: researchUse
trend / market / classics の調査が企画に「生きて」いるか、飾りでないか。
- ◎ 調査が判断を動かした痕跡が明確（調査前後で企画が変わったと分かる）
- ○ 調査を引用し反映している
- △ 引用しているだけ（結論に効いていない）
- ✗ 調査と無関係／grounding 不在
- 自動の参考値：`check_marketgap_citation`・evidence 接地

### ④ タイトルのエッジ — STEP2/STEP4 ／ eval: titleHook
この読者一人を掴むタイトルの鋭さ。
- ◎ この読者一人を掴む語彙が立っている（例「7人を、ひとりで背負わない」）
- ○ 惹きがある
- △ 平凡
- ✗ 「入門／教科書／5つの○○」級・長すぎ・全部問いかけ
- 自動の参考値：`check_book_title`（長さ・問いかけ型率）・`_GENERIC_TITLE_KW`

### ⑤ 著者ペルソナの前面化 — STEP3
設定した voiceStyle / format / 思想が**本当に出ている**か、棚で著者が立つか。
- ◎ 声と形式が企画に効き、棚で著者が一人の人物として立つ
- ○ 著者が立つ
- △ 設定が薄い／企画と無関係
- ✗ 役割名の羅列だけ・人物名衝突（`神崎玄一郎`/`里見ほたる` の few-shot 流用）
- 自動の参考値：`check_author_casting`（員数・2軸分散・薄さ・人物名衝突・selectionReason）

### ⑥ 型⇄局面の重さ両立 — STEP4
固有の生情報を「型」に抽象化しつつ、局面の重さ・焦燥・板挟みが伝わるか。
- ◎ 型に上げているのに重さが残る（読者が「これ自分だ」と腑に落ちる）
- ○ 型化できている
- △ 型化したら軽くなった／逆に生情報が漏れている
- ✗ 一般論の型・固有値（日付/人名/人数）のベタ貼り
- 自動の参考値：`check_body_abstraction`（本文の生情報漏れ。企画段では参考薄）

### ⑦ deliveryReason（入荷理由）の解像度 — STEP4 ／ 実UIでも確認
「なぜ今あなたに」が観測ソースに根ざし、読者が「見られている」と感じるか。
- ◎ 観測ソースを名指し、かつ説得力ある粒度（例「Driveの1on1メモ・6/5役員報告」）
- ○ ソースに言及
- △ 抽象的（「マネジメントのお悩み」級）
- ✗ ソース不在・定型文
- 自動の参考値：deliveryReason 観測ソース metric（`drv_/cal_/tsk_` 出現数。**半自動・参考値**）

### ⑧ 著者の体温・実体験 — STEP3
著者が（架空でも）本当にこの課題に向き合った原体験・口癖・思想を持つか。
- ◎ 原体験・口癖・思想が借り物でなく立っている（prefaceSample に体温）
- ○ 体温がある
- △ 薄い
- ✗ 無機質・属性の羅列
- 自動の参考値：persona 薄さフラグ（`_PERSONA_RICH_KW` 皆無）

### ⑨ 棚4冊の多様性 — STEP2-0 ／ 実UIでも確認
「裏は一貫・表は多様」になっているか。棚として意味を成すか。
- ◎ 読者局面への一貫性を保ちつつ theme/bookRole/utility/emotionalTone が4軸中3軸以上で分散
- ○ 多様
- △ 一部重複
- ✗ 全部同系・大カテゴリ止まり
- 自動の参考値：editor_chief の role 分散・voiceStyle×format 2軸

### ⑩ セレンディピティの当たり — STEP2-0（serendipity）
業務の「隣」へ本当に連れ出せているか。
- ◎ 業務の隣の教養へ連れ出し、読者の嗜好・許容度と整合した読書体験が立つ
- ○ 越境できている
- △ 距離不足（業務に近すぎ）／value で課題に回収する癖
- ✗ 課題の別領域への翻訳・即効ハウツー化
- 自動の参考値：`check_editor_chief_serendipity`（員数・adjacency 分散・棚書き文法・回収癖・距離不足）

## 5. ステップ別「人間が見る観点」（二度見しない割当）

| STEP | 出力 | 採点ディメンション | 主に見るセル |
|---|---|---|---|
| STEP1 reader | ReaderProfile | **採点なし**（①の前提として観測取りこぼしのみ目視） | 全セル |
| STEP2-0 editor_chief | ThemeAssignmentSet | ⑨（honmei）／⑩（serendipity） | M-H / N-H / S-S |
| STEP2 plan_owner×4 + leader | PlanProposal + verdict | ①②③④⑦前提 | **M-H / N-H** |
| STEP3 author_casting | AuthorCasting | ⑤⑧ | M-H / N-H |
| STEP4 author_preview | BookDraft | ⑥⑦④ | M-H / N-H |
| STEP5 cover | coverPrompt | 任意（規律のみ・実描画は層4 cover_lab） | — |

## 6. 合否ルール

- **足切り**：STEP2企画は **①が△以下＝不合格**（`eval_set.yaml` の `belowFloor` の人間版。閾値70の思想と同じ）。
- **セル合格**＝そのセルの全冊で ①≥○ かつ (⑨ or ⑩)≥○ かつ ✗ゼロ。
- **serendipity の①読み替え**：業務テーマへの直撃や whyNowForYou での課題接続は要求しない（課題に触れないのが仕様）。テーマ・章立てが読者の嗜好・許容度（readingGenres・serendipityTolerance）と整合し、読者の立場に普遍的に資するかで①を測る（`eval_judge.md` の serendipity 条項と同一）。
- **相対採点でも可**：改修前後の A/B 順位付け（どちらが良くなったか）で代替してよい。差分レビューではこちらが速い。

## 7. eval への還元（フライホイール）

- ①〜④は `eval/eval_set.yaml` の4観点と同一モノサシ。**◎/✗ を付けた企画はそのまま eval の新ケース候補**（◎→high_relevance、✗→low_relevance、△で迷い→borderlineCases）。
- ⑤〜⑩は judge に還元しない（採点レイヤが別）。
- 還元は大半を凍結後に回す。**borderline 追加だけは費用対効果が高いので随時**。
- **mock judge を人間の完全代理にしない**（leader relevance のスコア振れが記録済み）。

## 8. 記録形式（判定ログ）

`artifacts/prompt-review/<run_id>/verdicts.yaml`。各出力に `outputHash`（生JSONの sha256）を持たせ、改修後の差分レビューで「変わった出力だけ」再採点する。

```yaml
meta: { runId, reviewer: tetsuda, promptGitSha, cells: [S-H, S-S, M-H, N-H] }
cells:
  N-H:
    plans:
      plan_X:
        outputHash: <sha256>
        scores: { relevance: 3, differentiation: 2, researchUse: 2, titleHook: 3, deliveryReason: 2 }
        verdict: pass            # pass / revise / fail
        comment: "局面に直撃。marketGapやや弱い。"
    casting: { plan_X: { scores: { personaFront: 2, authorWarmth: 1 }, verdict: revise } }
    preview: { plan_X: { scores: { abstraction: 2, deliveryReason: 2, titleHook: 3 }, verdict: pass } }
    shelf:   { scores: { diversity: 3, serendipity: null }, verdict: pass }
```

> 採点キーは ① relevance ② differentiation ③ researchUse ④ titleHook ⑤ personaFront ⑥ abstraction ⑦ deliveryReason ⑧ authorWarmth ⑨ diversity ⑩ serendipity。
