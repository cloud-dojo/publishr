// Google Drive フォルダ選択（C4.1）。GIS でブラウザ用アクセストークンを取り、
// Google Picker でフォルダを選ばせ、選ばれた folderId を返す。
// サーバ観測（agents）の refresh token は別系統（/api/auth/google/start→callback）で、
// ここで得るのは Picker 表示専用の短命トークン。選択結果は /api/connect/drive-folders へ。

import { googleApiKey, googleAppId, googleClientId, isPickerConfigured } from "@/data/config";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const GAPI_SRC = "https://apis.google.com/js/api.js";
// フォルダ配下のテキストを観測が列挙する前提＝drive.readonly（observe の resolve_scopes と一致）。
const DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly";
const FOLDER_MIME = "application/vnd.google-apps.folder";

export interface PickedFolder {
  folderId: string;
  name: string;
}

const scriptCache = new Map<string, Promise<void>>();

function loadScript(src: string): Promise<void> {
  if (typeof document === "undefined") return Promise.reject(new Error("no document"));
  const cached = scriptCache.get(src);
  if (cached) return cached;
  const p = new Promise<void>((resolve, reject) => {
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.onload = () => resolve();
    el.onerror = () => {
      scriptCache.delete(src); // 失敗を握り続けない＝再試行で読み直せる
      reject(new Error(`failed to load ${src}`));
    };
    document.head.appendChild(el);
  });
  scriptCache.set(src, p);
  return p;
}

let pickerApiLoaded = false;
function loadPickerApi(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (pickerApiLoaded) return resolve();
    const gapi = window.gapi;
    if (!gapi) return reject(new Error("gapi unavailable"));
    gapi.load("picker", () => {
      pickerApiLoaded = true;
      resolve();
    });
  });
}

function getAccessToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    const oauth2 = window.google?.accounts?.oauth2;
    if (!oauth2) return reject(new Error("GIS unavailable"));
    const client = oauth2.initTokenClient({
      client_id: googleClientId,
      scope: DRIVE_SCOPE,
      callback: (resp) => {
        if (resp.access_token) resolve(resp.access_token);
        else reject(new Error(resp.error || "no access_token"));
      },
      // 同意ポップアップを閉じた/失敗した場合に reject（Promiseが宙吊りになるのを防ぐ）。
      error_callback: (err) => reject(new Error(err.message || err.type || "token request failed")),
    });
    client.requestAccessToken({ prompt: "" });
  });
}

/**
 * Drive フォルダ選択ダイアログを開き、選ばれたフォルダを返す（キャンセル時は空配列）。
 * 未設定（client_id / API キー欠落）なら例外。呼び出し側で isPickerConfigured を確認すること。
 */
export async function pickDriveFolders(): Promise<PickedFolder[]> {
  if (!isPickerConfigured) throw new Error("Google Picker is not configured");
  await Promise.all([loadScript(GIS_SRC), loadScript(GAPI_SRC)]);
  await loadPickerApi();
  const token = await getAccessToken();

  return new Promise<PickedFolder[]>((resolve, reject) => {
    const picker = window.google?.picker;
    if (!picker) return reject(new Error("Picker API unavailable"));
    const view = new picker.DocsView(picker.ViewId.FOLDERS)
      .setSelectFolderEnabled(true)
      .setIncludeFolders(true)
      .setMimeTypes(FOLDER_MIME);
    const builder = new picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(token)
      .setDeveloperKey(googleApiKey)
      .setCallback((data) => {
        if (data.action === picker.Action.PICKED) {
          resolve((data.docs ?? []).map((d) => ({ folderId: d.id, name: d.name })));
        } else if (data.action === picker.Action.CANCEL) {
          resolve([]);
        }
      });
    if (googleAppId) builder.setAppId(googleAppId);
    builder.build().setVisible(true);
  });
}
