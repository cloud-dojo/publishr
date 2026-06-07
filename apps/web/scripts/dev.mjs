// ローカル開発サーバのモード別ランチャー（ゼロ依存・クロスプラットフォーム）。
//   node scripts/dev.mjs mock      … 純mock・認証なし（最速のUI/遷移確認）
//   node scripts/dev.mjs emulator  … firestore＋Firebaseエミュレータ（実ルール/実認証をローカル検証）
//   node scripts/dev.mjs           … 既定。.env.local をそのまま使う
//
// Next.js は @next/env で .env* を process.env に読み込むが、既に process.env に
// セット済みのキーは上書きしない。よってここで先に立てた値が勝つ。
import { spawn } from "node:child_process";

const mode = process.argv[2] ?? "default";

if (mode === "mock") {
  // mockデータ＋Firebase鍵を空に→ isFirebaseConfigured=false（実Googleログインなし）。
  process.env.NEXT_PUBLIC_DATA_SOURCE = "mock";
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY = "";
  process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = "";
  process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR = "0";
} else if (mode === "emulator") {
  // firestoreモード＋エミュレータ接続フラグ（.env.local の Firebase 鍵をそのまま使う）。
  process.env.NEXT_PUBLIC_DATA_SOURCE = "firestore";
  process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR = "1";
} else if (mode !== "default") {
  console.error(`不明なモード: ${mode}（mock | emulator | 省略 のいずれか）`);
  process.exit(1);
}

console.log(`[dev.mjs] mode=${mode} DATA_SOURCE=${process.env.NEXT_PUBLIC_DATA_SOURCE ?? "(.env.local)"} EMULATOR=${process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR ?? "0"}`);

const child = spawn("next", ["dev"], { stdio: "inherit", shell: true });
child.on("exit", (code) => process.exit(code ?? 0));
