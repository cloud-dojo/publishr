# ローカル・サンドボックス（本番に触れず高速に確認する）

実アカウント＋App Hostingビルドで毎回確認すると遅く、登録/オンボーディングの反復確認も
しづらい。ローカルで完結する2系統を用意した。普段は **A（mock）** で高速反復し、
ルール/認証が絡む時だけ **B（エミュレータ）** で確証する。

## A. 純mockローカル（最速・実認証なし）

```
npm run dev:mock        # ルートから。http://localhost:3000
```

- `NEXT_PUBLIC_DATA_SOURCE=mock` ＋ Firebase鍵を空に → `isFirebaseConfigured=false`。
  実Googleログインのポップアップは出ず、データは fixtures（決定的・オフライン）。
- ログインは localStorage の initialProfile 有無で遷移（未設定→/onboarding、設定済→/）。
- **新規ユーザーの再現**：シークレット（プライベート）ウィンドウで開くたびに「まっさら」。
- **「初期設定済み」をリセット**：DevTools → Application → Local Storage で
  `publishr.initialProfile.*` を消す（または別のシークレットウィンドウ）。
- 用途：UI・画面遷移・オンボーディング/アカウント/プロフィール編集の反復確認。
- ホットリロードなのでビルド待ちゼロ。

## B. Firebaseエミュレータ（実ルール・実認証をローカル検証）

実Firestoreルール・認証uid・登録の永続を、本番に触れず偽ユーザーで検証する。
**前提：Java（JDK 11+）が必要**（Firestoreエミュレータの実行要件）。

ターミナル2枚で：

```
# 1枚目：エミュレータ（Auth :9099 / Firestore :8080 / UI :4000）
npm run emulators

# 2枚目：Webをエミュレータ接続モードで起動
npm run dev:emulator        # http://localhost:3000
```

- `NEXT_PUBLIC_DATA_SOURCE=firestore` ＋ `NEXT_PUBLIC_USE_FIREBASE_EMULATOR=1`。
  `.env.local` の Firebase 鍵はそのまま使う（エミュレータはダミーでも可）。
- firebase.ts が `connectAuthEmulator` / `connectFirestoreEmulator` でローカルに接続。
- Auth エミュレータは偽ユーザーを自由に作成（実Googleアカウント不要）。
- Firestore データは揮発（停止で消える）。エミュレータUI http://localhost:4000 で中身を確認可。
- ルール（`firestore.rules`）はエミュレータが自動ロードするので、変更を本番デプロイ前に検証できる。
- 用途：`hasCompletedOnboarding` のFirestore読取、登録の永続、ルール緩和の影響など。

## C. 本番（App Hosting）

A/B で固めた後の**最終確認だけ**にする。`git push origin main` でビルド→デプロイ。
Firestoreルールは `firebase deploy --only firestore:rules`。

## モード早見

| コマンド | DATA_SOURCE | 認証 | データ | 用途 |
|---|---|---|---|---|
| `npm run dev:mock` | mock | なし | fixtures | UI/遷移/登録の高速反復 |
| `npm run dev:emulator` ＋ `npm run emulators` | firestore | エミュレータ | ローカルFirestore | ルール/認証/永続の検証 |
| `npm run dev:web` | `.env.local`次第 | `.env.local`次第 | 同左 | 既定（本番鍵で実接続も可） |

> 実装メモ：モード切替は `apps/web/scripts/dev.mjs`（ゼロ依存ランチャー）が
> `process.env` を先に立てて `next dev` を spawn する。Next.js は既存 process.env を
> 上書きしないため、ここで指定した値が `.env.local` より優先される。
