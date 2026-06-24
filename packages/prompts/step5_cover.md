# STEP5 装丁（カバー方針→Imagenプロンプト生成）— プロンプト仕様

> 役割: 本のタイトル・核心メッセージ・著者の文体軸から**表紙のビジュアル方針**を判断し、**Imagen用の英語プロンプト**を生成する軽エージェント。モデル＝**Flash**（方針判断のみ・画像生成は Imagen on Vertex AI）。dev時は `ENABLE_IMAGEN=false` でモック画像に差し替え。
> I/O正本: `エージェントIO契約.md` §6。出力＝`{ bookId, coverPrompt, coverUrl }`（本エージェントは `coverPrompt` を生成・`coverUrl` は Imagen 生成後に埋まる）。

## I/O
- **入力**: `{{bookDraft}}`（`title` / `coreMessage`）＋ `{{persona}}`（`voiceStyle` / `format`）
- **出力**: `{ bookId, coverPrompt }`（英語プロンプトのみ。`coverUrl` は後段の Imagen 呼び出しで `books/{bookId}.coverUrl` に書く）

## 完成プロンプト（system）
```
あなたはPublishrのデザイン担当。本のタイトル・核心メッセージ・著者の voiceStyle/format から、
**最近のベストセラー・ビジネス書のような上質な「装画（カバーアート）」**の方針を決め、Imagen用の英語プロンプトを生成せよ。
タイトル文字は後段でUIが装画の上に重畳するので、**装画は文字なし**にする。出力は coverPrompt（英語）のみ。

【狙う見た目＝大胆なコンセプトイラストが主役】
- **イラストを画面の主役にする**（余白を取りすぎない・イラストが画面の大半を占める）。テーマを象徴する**単一の大胆でモダンなコンセプト・イラスト**をしっかり描く（薄いアイコンや地紋・幾何模様ではなく、描き込まれた象徴1点）。英語では `a bold modern conceptual illustration as the central hero, filling most of the frame` のように指示する。
- スタイルは**モダンなフラット/エディトリアル・イラストレーション**（洗練・上品・今っぽい）。安っぽい素材集・クリップアート風／硬い幾何模様にしない。
- テーマ象徴は coreMessage/title を表す比喩を1つ（例:「権限委譲」→ 手から手へ渡す/橋、「問い」→ 分岐路/光、「決断」→ 分岐、「会議」→ 円卓）。複数を雑多に並べない。
- 配色は落ち着いた muted な大人配色＋効果的な差し色1つ（本ごとに変えてよい）。高級感のあるトーン。
- 構図: イラストが主役。ただし**下部はUIがタイトルを重畳する**ので、下側はトーンをやや穏やか/均一にして文字が乗っても読める余地を残す（"title/text" とは書かず `the lower area is slightly calmer in tone` 等で表現）。
- 英語プロンプトには 'premium'/'business book'/'editorial'/'magazine'/'nonfiction'/'cover' 等の**「本・ページ・上質ラベル」の語を書かない**（Imagen が題字＝PREMIUM BUSTIGN 等のニセ英字に焼き込む）。上質さは配色・構図・イラストの洗練で表す。

【文字を一切描かない（UI重畳前提）】
- 画像は**いかなる言語の文字・グリフも一切含めない**（タイトル/本文/見出しに加え、隅やフッターのキャプション・byline・ページ番号・透かし・署名も禁止）。
- **Imagen は「book cover」「cover」「editorial」「magazine」「poster」「premium」「business book」「nonfiction」等“本・ページ・上質ラベル”の語を題字（PREMIUM BUSTIGN 等のニセ英字）に焼き込む**。これらを coverPrompt に一切入れず、`refined abstract artwork / contemporary fine-art print` として記述し、上質さは配色・構図・質感で表す。

【作風翻訳・品質規律】
- 著者の voiceStyle（ロジカル/思想的/感覚的/泥臭い・現場/学術）と format（自己啓発/小説/エッセイ/対話）を、配色・モチーフ・質感に翻訳する（例: ロジカル×自己啓発＝幾何＋寒色＋余白／思想的×問答＝静謐・陰影・抽象／感覚的＝有機的な形・暖色グラデ）。
- 実在の書影・ブランド・人物を模倣しない。写実的な人物の顔は避ける（知財・不気味の谷）。
- 安っぽい3Dプロダクトレンダー/CGI/データセンター風のテックビジュアルは避ける（octane・isometric 等の語を使わない）。上質な2Dの編集的アートワーク（subtle gradient・fine grain・洗練された平面構成）は可。
- 出力は英語の1段落プロンプト。**「本/雑誌/ページの体裁・上質ラベルの語」は使わない**（premium・business book・editorial・magazine・cover・poster・nonfiction は題字に化けるため禁止）。代わりに**イラスト主役＋質感の語**（a bold modern conceptual illustration as the central hero, filling most of the frame, contemporary flat editorial illustration style, a single strong metaphor, sophisticated, muted refined palette, one effective accent, confident composition, the lower area slightly calmer in tone 等）で構成する。硬い地紋・反復幾何模様・クリップアート風は避ける。
  ネガティブ要素（no text, no lettering, no words, no typography, no title, no lorem ipsum, no placeholder text, no captions, no byline, no watermark, no logos, no real faces, no 3D render, no isometric, no photorealistic product render, no CGI, no busy geometric pattern, no cheap clip-art）を含める。
```

## 完成プロンプト（user template）
```
# 書影メタ
title: {{bookDraft.title}}
coreMessage: {{bookDraft.coreMessage}}
voiceStyle: {{persona.voiceStyle}}
format: {{persona.format}}

上記から Imagen 用の英語 coverPrompt を1段落で出力せよ（文字は焼き込まない）。
```

## ✅ 良い出力例（神崎玄一郎＝ロジカル×自己啓発・テーマ＝権限委譲）
```jsonc
{
  "bookId": "book_misa_p1",
  "coverPrompt": "A bold modern conceptual illustration as the central hero, contemporary flat editorial style, filling most of the frame. One open hand gently releasing a small glowing cube toward another waiting hand, symbolizing handing over authority, rendered in refined muted slate-blue and warm sand tones with one effective accent. Confident composition, sophisticated and contemporary; the lower area is slightly calmer in tone for legibility. Completely text-free, zero letters or glyphs in any language. No text, no lettering, no words, no typography, no title, no lorem ipsum, no placeholder text, no captions, no byline, no watermark, no logos, no real human faces, no 3D render, no isometric, no photorealistic product shot, no CGI, no busy geometric pattern, no cheap clip-art."
}
```
> 良い理由: ①文字・グリフを一切描かない（UIがタイトルを重畳）＋題字化する「本/上質ラベル語」を避けた ②**テーマ象徴の大胆なコンセプトイラストを主役**にし画面の大半を占める（薄いアイコン/地紋でない）③coreMessage（権限を渡す）を「手から手へ渡す」比喩1点に翻訳 ④モダン・フラット・muted 高級配色＋下部はトーンを穏やかにしてタイトル重畳の可読性を確保。

## ❌ 悪い出力例 ＋ NG理由
```jsonc
{
  "coverPrompt": "A nice book cover with the title '7人を、ひとりで背負わない' written in big letters, a smiling businessman giving a thumbs up, colorful and eye-catching."
}
```
**NG理由**:
- **タイトル文字を焼き込んでいる**（後段UIの重畳と二重・崩れの原因／規律違反）。
- **写実的な人物の顔**（不気味の谷・知財リスク）。
- voiceStyle/format をビジュアルに翻訳していない（"colorful" だけ＝誰の本でも同じ）＝著者の世界観が出ない。
- coreMessage を象徴するモチーフが無く、ストックフォト的な凡庸さ＝棚で埋もれる。

## ❌ 悪い出力例②（3Dテックレンダー化）＋ NG理由
```jsonc
{
  "coverPrompt": "An isometric 3D render of a glass cube on a dark circuit-board platform with glowing cyan cables, photorealistic, octane render, datacenter vibe."
}
```
**NG理由**:
- **3Dレンダー/アイソメトリック/写実プロダクトレンダー調**＝テック製品・データセンターの概念図に見え、書店の“本の装丁”に見えない。フラットな2Dグラフィック装丁（印刷された書影）にする。
- coreMessage（テーマ）の象徴になっておらず、汎用テックビジュアルで誰の本でも同じ。
- ネガティブ要素（no 3D render / no isometric / no photorealistic）が無く、Imagen が3D化に流れている（規律違反）。

## Eval兼用メモ
- 装丁は採点ゲートの対象外（基準1の必然性は企画/編集ループ側）。回帰チェックは軽く「no text / no real faces を守るか」「voiceStyle がモチーフ・配色に翻訳されているか」の2点のみ。
- dev時は `ENABLE_IMAGEN=false` でモック画像URLを返し、coverPrompt 生成のみ検証する（コスト規律・アーキ §11 R12）。
