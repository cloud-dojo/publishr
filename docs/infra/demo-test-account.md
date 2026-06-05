# Publishr デモ・テスト用 Google アカウント

> **更新日**: 2026-06-05
> **用途**: エージェント観測ツール(C1.1.1)のテスト・デモ録画用のサンプルデータアカウント

---

## アカウント情報

| 項目 | 値 |
|---|---|
| 名前 | Sakura Misaki（佐倉美咲） |
| メールアドレス | `publishr.hackathon@gmail.com` |
| 用途 | 観測ツールのOAuthテスト・デモ動画録画 |
| OAuthテストユーザー登録 | ✅ 済（Google Cloud Console > OAuth同意画面） |

---

## Google Drive フォルダ構成

```
Publishr_佐倉美咲/
  ├── デモ動画用/     ← .md ファイル（画面映え重視・デモ録画用）
  └── 本番テスト用/   ← .pptx / .xlsx / .docx（実観測テスト用）
```

| フォルダ名 | フォルダID | 用途 |
|---|---|---|
| **デモ動画用** | `1Bdu_II4krrCdMXCLoBYOWcBGhG-zwoC4` | デモ録画時に観測ツールへ渡すフォルダID |
| **本番テスト用** | `1XZS8F6ZTx8dorrhGxxcA7mrGkREM-gN7` | 実ファイル形式での観測テスト用フォルダID |

### ドライブURL
- デモ動画用: https://drive.google.com/drive/folders/1Bdu_II4krrCdMXCLoBYOWcBGhG-zwoC4
- 本番テスト用: https://drive.google.com/drive/folders/1XZS8F6ZTx8dorrhGxxcA7mrGkREM-gN7

---

## ファイル一覧（共通・10本）

| # | ファイル名 | 形式（デモ用） | 形式（本番テスト用） | シグナル |
|---|---|---|---|---|
| 01 | しずく天然水_2026春リニューアル企画書 | `.md` | `.pptx` | 意思決定への自信のなさ |
| 02 | チーム体制_役割分担表 | `.md` | `.xlsx` | 7名・年上部下の存在 |
| 03 | 課長就任メモ_最初の90日 | `.md` | `.docx` | 手探り・読む時間がない |
| 04 | 上期_個人目標とチーム目標 | `.md` | `.docx` | 評価への不安 |
| 05 | 競合A社_新商品分析 | `.md` | `.pptx` | 意思決定の軸 |
| 06 | 1on1_議事メモ集 | `.md` | `.docx` | ピープルマネジメントの悩み |
| 07 | マーケ部_中期戦略メモ | `.md` | `.docx` | 戦略思考への欲求 |
| 08 | 会議ファシリテーション_振り返りメモ | `.md` | `.docx` | ファシリスキルへの課題意識 |
| 09 | 読書メモ_1兆ドルコーチ（途中） | `.md` | `.docx` | 積読・Publishrの存在意義 |
| 10 | 来期_個人キャリアメモ | `.md` | `.docx` | 成長欲求 |

ソースファイル（ローカル）: `C:\Users\ytets\publishr_other\demo\サンプルデータ_3ソース\`

---

## カレンダー・タスクデータ

| ソース | データ場所 | 投入状況 |
|---|---|---|
| Google Calendar | `C:\Users\ytets\publishr_other\demo\サンプルデータ_3ソース\カレンダーデータ.md` | 🔜 未投入 |
| Google Tasks | `C:\Users\ytets\publishr_other\demo\サンプルデータ_3ソース\タスクデータ.md` | 🔜 未投入 |

> カレンダー・タスクはMTG後に手動で投入予定。

---

## 観測ツール実装時の参考

- Drive Picker方式（G1-13）が確定後、フォルダIDをどちら渡すか決める
- テスト時: `本番テスト用` フォルダIDを指定
- デモ録画時: `デモ動画用` フォルダIDを指定
- WBS参照: C1.1.1（観測ツール実装）/ C6.2（デモのデータ戦略）
