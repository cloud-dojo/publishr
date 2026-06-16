// データ取得元と各種タイミング設定。

export type DataSource = "bff" | "mock" | "firestore";

export const dataSource: DataSource =
  (process.env.NEXT_PUBLIC_DATA_SOURCE as DataSource) ?? "bff";

export const apiUrl: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// 表紙画像(Imagen)の表示元を解決する。実 Imagen 表紙は非公開 GCS の object パス
// （`covers/...png`）で coverUrl に入るため、BFF のサーバ側 read 配信口に解決する。
// http(s) URL はそのまま。未設定(null)は undefined＝CSS バリアントの装丁にフォールバック。
export function coverSrc(bookId: string, coverUrl?: string | null): string | undefined {
  if (!coverUrl) return undefined;
  if (coverUrl.startsWith("http")) return coverUrl;
  return `${apiUrl}/api/books/${encodeURIComponent(bookId)}/cover`;
}

// Firebase クライアント設定（公開キー・コミット可）。
// 値は apphosting.yaml / .env.local の NEXT_PUBLIC_FIREBASE_* で投入する。
// 未設定（mock運用中）でもアプリが動くよう、firebase.ts 側で空判定する。
export const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET ?? "",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ?? "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID ?? "",
};

export const isFirebaseConfigured: boolean =
  firebaseConfig.apiKey !== "" && firebaseConfig.projectId !== "";

// Google Picker（Drive フォルダ選択 UI・C4.1）の公開設定。
// すべて公開値（クライアント側・GCP コンソールで origin/referrer を制限する）。
// apphosting.yaml / .env.local の NEXT_PUBLIC_GOOGLE_* で投入する:
//   NEXT_PUBLIC_GOOGLE_CLIENT_ID … OAuth 2.0 クライアントID（Web アプリ）
//   NEXT_PUBLIC_GOOGLE_API_KEY   … API キー（Picker の developerKey・要 Picker API 有効化）
//   NEXT_PUBLIC_GOOGLE_APP_ID    … GCP プロジェクト番号（任意）
export const googleClientId: string = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
export const googleApiKey: string = process.env.NEXT_PUBLIC_GOOGLE_API_KEY ?? "";
export const googleAppId: string = process.env.NEXT_PUBLIC_GOOGLE_APP_ID ?? "";

// Picker を出せる構成か（client_id ＋ API キーが揃っているか）。未設定なら UI は隠す。
export const isPickerConfigured: boolean = googleClientId !== "" && googleApiKey !== "";

// ローカルの Firebase エミュレータ（Auth/Firestore）に接続するか。
// dev:emulator スクリプトが NEXT_PUBLIC_USE_FIREBASE_EMULATOR=1 を立てる。
export const useFirebaseEmulator: boolean =
  process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR === "1";

// 予約→執筆→入荷 の体感タイマー（ミリ秒）。デモ用に再調整可能。
export const timing = {
  reserveToWriting: 2200,
  writingToPublished: 5200,
  pollInterval: 1500,
};

export const DEMO_USER_ID = "u_sakura";
