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

// 表紙の簡易フォールバック（C5.1 表紙保険）。
// imagen 表紙(coverUrl)が無いとき、表紙を「シックな暗色グラデ＋タイトル左上」のミニマル装丁にする。
// 既定 ON（imagen 連携が間に合わない前提の標準表紙）。coverUrl があればそちらを優先する。
// 従来の CSS フラット装丁に戻したい場合のみ NEXT_PUBLIC_SIMPLE_COVER=0 で無効化する。
export const simpleCoverFallback: boolean =
  process.env.NEXT_PUBLIC_SIMPLE_COVER !== "0";

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

// 「今すぐ企画」手動トリガーを表示してよい uid の allowlist（方針A・デモ限定）。
// バックエンドの ALLOWED_TRIGGER_UIDS と対。実 Vertex 企画＝課金なので一般ユーザーには出さない。
// build 時に NEXT_PUBLIC_TRIGGER_UIDS（カンマ区切り）で佐倉の実 Firebase UID を投入する。
// 未設定なら DEMO_USER_ID のみ（＝本番は実質非表示／ローカル dev は u_sakura で表示される安全側）。
const triggerUids: string[] = (process.env.NEXT_PUBLIC_TRIGGER_UIDS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

// 無認証公開ショーケースで表示/参照する実デモ owner（佐倉の実 Firebase UID）。
// BFF の books/plans はこの owner にスコープ済み（deps.py の demo_uid）。apphosting の
// NEXT_PUBLIC_TRIGGER_UIDS（=佐倉の実 UID）を流用し、未設定（mock/local）は DEMO_USER_ID にフォールバック。
export const DEMO_OWNER_UID = triggerUids[0] ?? DEMO_USER_ID;

/** 手動企画トリガーをこの uid に見せてよいか（方針A: allowlist 一致のみ）。 */
export function canManualTrigger(uid: string | null | undefined): boolean {
  const allow = triggerUids.length > 0 ? triggerUids : [DEMO_USER_ID];
  return allow.includes(uid ?? DEMO_USER_ID);
}

// 無認証デモ公開（②G）でライブ生成の「per-client 日次上限」を数える単位。
// localStorage に UUID を発行・永続（クリア/別ブラウザで別 client＝回避可は承知の上のソフト制限。
// 本丸はサーバ側のグローバル日次上限＋Cloud Billing）。
export function getDemoClientId(): string {
  if (typeof window === "undefined") return "anon";
  const KEY = "publishr.demoClientId";
  try {
    let id = window.localStorage.getItem(KEY);
    if (!id) {
      id =
        window.crypto?.randomUUID?.() ??
        `c_${Date.now()}_${Math.random().toString(36).slice(2)}`;
      window.localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    return "anon";
  }
}

// ②G: 無認証ライブ生成ボタンを有効化するフラグ（既定OFF=ショーケースは読み取り専用＝安全）。
// 本番デモは NEXT_PUBLIC_DEMO_LIVE_GEN=1（web）と サーバ側 PUBLISHR_DEMO_RATE_*（Cloud Run）を
// 同時に立てて初めて開放する。コードのデプロイだけでは晒されない（フラグOFFでボタン非表示）。
export const demoLiveGenEnabled: boolean = process.env.NEXT_PUBLIC_DEMO_LIVE_GEN === "1";

/**
 * 表紙画像の URL を返す。
 * - coverUrl が GCS object パス（covers/...png・非公開バケット）なら、BFF
 *   `/api/books/{id}/cover` 経由のサーバ側 read 配信 URL を返す（`<img src>` から GCS を直接
 *   引かせない）。※coverUrl をそのまま返すと web 相対パスに解決され 404 になる。
 * - 既に http(s) の外部 URL ならそのまま返す（将来用）。
 * - 未設定（null/空）なら null を返し、BookCover は CSS の文字表紙（装丁）にフォールバックする
 *   （静的プレースホルダ画像には落とさない＝Kindle 風の文字中心デザインを既定にする）。
 */
export function coverSrc(bookId: string, coverUrl: string | null | undefined): string | null {
  if (!coverUrl) return null;
  if (coverUrl.startsWith("http")) return coverUrl;
  return `${apiUrl}/api/books/${encodeURIComponent(bookId)}/cover`;
}
