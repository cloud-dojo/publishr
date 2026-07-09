// Google Identity Services（GIS）＋ Google Picker の最小型宣言（C4.1）。
// 公式の型パッケージは入れず、lib/googlePicker.ts が使う面だけを宣言する。
export {};

interface GooglePickerDocsView {
  setSelectFolderEnabled(enabled: boolean): GooglePickerDocsView;
  setIncludeFolders(include: boolean): GooglePickerDocsView;
  setMimeTypes(mimeTypes: string): GooglePickerDocsView;
}

interface GooglePickerBuilt {
  setVisible(visible: boolean): void;
}

interface GooglePickerBuilder {
  addView(view: GooglePickerDocsView): GooglePickerBuilder;
  setOAuthToken(token: string): GooglePickerBuilder;
  setDeveloperKey(key: string): GooglePickerBuilder;
  setAppId(appId: string): GooglePickerBuilder;
  setCallback(cb: (data: GooglePickerResponse) => void): GooglePickerBuilder;
  build(): GooglePickerBuilt;
}

interface GooglePickerResponse {
  action: string;
  docs?: Array<{ id: string; name: string; mimeType?: string }>;
}

interface GooglePickerNamespace {
  DocsView: new (viewId?: unknown) => GooglePickerDocsView;
  PickerBuilder: new () => GooglePickerBuilder;
  ViewId: { FOLDERS: unknown; DOCS: unknown };
  Action: { PICKED: string; CANCEL: string };
}

interface GoogleTokenClient {
  requestAccessToken(overrideConfig?: { prompt?: string }): void;
}

interface GoogleOAuth2 {
  initTokenClient(config: {
    client_id: string;
    scope: string;
    callback: (resp: { access_token?: string; error?: string }) => void;
    error_callback?: (err: { type?: string; message?: string }) => void;
  }): GoogleTokenClient;
}

declare global {
  interface Window {
    gapi?: { load: (api: string, cb: () => void) => void };
    google?: {
      accounts?: { oauth2?: GoogleOAuth2 };
      picker?: GooglePickerNamespace;
    };
  }
}
