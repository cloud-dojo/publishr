// Firebase クライアント初期化（遅延・ガード付き）。
// - NEXT_PUBLIC_FIREBASE_* が未設定（mock運用中）でも import 時に落ちないよう、
//   初期化は getter 経由・設定がある時だけ実行する。
// - サーバ（SSR/ビルド）では初期化しない（ブラウザAPI依存のため）。
"use client";

import { getApps, initializeApp, type FirebaseApp } from "firebase/app";
import {
  GoogleAuthProvider,
  connectAuthEmulator,
  getAuth,
  onAuthStateChanged,
  signInWithCustomToken,
  signInWithPopup,
  signOut as fbSignOut,
  type Auth,
  type User as FirebaseUser,
} from "firebase/auth";
import { connectFirestoreEmulator, getFirestore, type Firestore } from "firebase/firestore";

import { firebaseConfig, isFirebaseConfigured, useFirebaseEmulator } from "@/data/config";

let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;
let _db: Firestore | null = null;

function ready(): boolean {
  return typeof window !== "undefined" && isFirebaseConfigured;
}

export function getFirebaseApp(): FirebaseApp | null {
  if (!ready()) return null;
  if (!_app) _app = getApps()[0] ?? initializeApp(firebaseConfig);
  return _app;
}

export function getFirebaseAuth(): Auth | null {
  const app = getFirebaseApp();
  if (!app) return null;
  if (!_auth) {
    _auth = getAuth(app);
    if (useFirebaseEmulator) {
      // ローカルAuthエミュレータへ接続（実Googleアカウント不要・偽ユーザーで検証）。
      connectAuthEmulator(_auth, "http://127.0.0.1:9099", { disableWarnings: true });
    }
  }
  return _auth;
}

export function getDb(): Firestore | null {
  const app = getFirebaseApp();
  if (!app) return null;
  if (!_db) {
    _db = getFirestore(app);
    if (useFirebaseEmulator) {
      // ローカルFirestoreエミュレータへ接続（本番データに触れずルール検証）。
      connectFirestoreEmulator(_db, "127.0.0.1", 8080);
    }
  }
  return _db;
}

/** Googleサインイン。Firebase未設定（mock）の時は null を返す（呼び出し側でフォールバック）。 */
export async function signInWithGoogle(): Promise<FirebaseUser | null> {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  const provider = new GoogleAuthProvider();
  const cred = await signInWithPopup(auth, provider);
  return cred.user;
}

/** デモ用カスタムトークンでサインイン（I-32）。BFF から受け取ったトークンを渡す。 */
export async function signInWithDemoToken(token: string): Promise<FirebaseUser | null> {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  const cred = await signInWithCustomToken(auth, token);
  return cred.user;
}

export async function signOutUser(): Promise<void> {
  const auth = getFirebaseAuth();
  if (auth) await fbSignOut(auth);
}

/** 認証状態の購読。未設定時は即 null を通知して no-op unsubscribe を返す。 */
export function watchAuth(cb: (user: FirebaseUser | null) => void): () => void {
  const auth = getFirebaseAuth();
  if (!auth) {
    cb(null);
    return () => {};
  }
  return onAuthStateChanged(auth, cb);
}

export type { FirebaseUser };
