// データ取得元と各種タイミング設定。

export type DataSource = "bff" | "mock";

export const dataSource: DataSource =
  (process.env.NEXT_PUBLIC_DATA_SOURCE as DataSource) ?? "bff";

export const apiUrl: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// 予約→執筆→入荷 の体感タイマー（ミリ秒）。デモ用に再調整可能。
export const timing = {
  reserveToWriting: 2200,
  writingToPublished: 5200,
  pollInterval: 1500,
};

export const DEMO_USER_ID = "u_tadokoro";
