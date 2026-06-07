// データ取得元と各種タイミング設定。

export type DataSource = "bff" | "mock" | "firestore";

export const dataSource: DataSource =
  (process.env.NEXT_PUBLIC_DATA_SOURCE as DataSource) ?? "bff";

export const apiUrl: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
