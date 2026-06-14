"use client";

// 観測ソース連携（Google Drive/Calendar/Tasks）の共有 UI。
// /connect（オンボーディング）と /account（管理）の両方から使う＝実フローを1か所に集約。
//
// 実態に合わせた設計:
//  - OAuth 同意は「1回」で3スコープまとめて付与される（BFF /api/auth/google/start →
//    Google 同意 → /callback がサーバ側で connectedSources.{drive,calendar,tasks}.enabled を設定）。
//    なので連携ボタンは3独立ではなく「Googleと連携」1つ。各ソースは状態表示。
//  - Drive だけ追加で「観測フォルダを選ぶ」(Picker) が要る（folderIds が必要）。
//  - 状態の正本はサーバの connectedSources（initial prop で実値を反映）。mock 時は localStorage。

import { useState } from "react";

import type { ConnectedSources } from "@publishr/shared-schema";

import { apiUrl, isFirebaseConfigured, isPickerConfigured } from "@/data/config";
import { getConnectedSources, setSourceConnectedLocal, type ConnectSource } from "@/data/user-writes";
import { getFirebaseAuth } from "@/lib/firebase";
import { pickDriveFolders, type PickedFolder } from "@/lib/googlePicker";

const SOURCES: { key: ConnectSource; icon: string; name: string; desc: string }[] = [
  { key: "drive", icon: "📁", name: "Google Drive", desc: "業務資料・関心フォルダのテキストを読み取ります。" },
  { key: "calendar", icon: "📅", name: "Google Calendar", desc: "スケジュール・役割の文脈を読み取ります。" },
  { key: "tasks", icon: "✓", name: "Google Tasks", desc: "タスク・優先度の文脈を読み取ります。" },
];

// 初期状態: 実 connectedSources（サーバ正本）を優先し、無ければ localStorage（mock）にフォールバック。
function seedConnected(initial?: ConnectedSources | null): Record<ConnectSource, boolean> {
  const ls = getConnectedSources();
  if (!initial) return ls;
  return {
    drive: initial.drive?.enabled ?? ls.drive,
    calendar: initial.calendar?.enabled ?? ls.calendar,
    tasks: initial.tasks?.enabled ?? ls.tasks,
  };
}

export function ConnectSources({ initial }: { initial?: ConnectedSources | null }) {
  const [connected, setConnected] = useState<Record<ConnectSource, boolean>>(() => seedConnected(initial));
  const [folders, setFolders] = useState<PickedFolder[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1回の同意で3スコープ付与。ログイン時は実 OAuth、未設定（mock）時は localStorage で擬似完了。
  const onConnect = async () => {
    setError(null);
    if (isFirebaseConfigured) {
      try {
        const token = await getFirebaseAuth()?.currentUser?.getIdToken();
        const res = await fetch(`${apiUrl}/api/auth/google/start`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error(`連携の開始に失敗しました (${res.status})`);
        const data = (await res.json()) as { authUrl?: string };
        if (!data.authUrl) throw new Error("authUrl が取得できませんでした");
        window.location.href = data.authUrl;
      } catch (e) {
        setError(e instanceof Error ? e.message : "連携に失敗しました");
      }
      return;
    }
    (["drive", "calendar", "tasks"] as ConnectSource[]).forEach((k) => setSourceConnectedLocal(k, true));
    setConnected({ drive: true, calendar: true, tasks: true });
  };

  // Drive Picker: フォルダ選択 → サーバ保存（POST /api/connect/drive-folders）。
  const onPickFolders = async () => {
    setError(null);
    setBusy(true);
    try {
      const picked = await pickDriveFolders();
      if (picked.length === 0) return; // キャンセル
      const token = await getFirebaseAuth()?.currentUser?.getIdToken();
      const res = await fetch(`${apiUrl}/api/connect/drive-folders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          folderIds: picked.map((f) => f.folderId),
          labels: picked.map((f) => ({ folderId: f.folderId, label: "" })),
        }),
      });
      if (!res.ok) throw new Error(`フォルダ保存に失敗しました (${res.status})`);
      setFolders(picked);
      setConnected((c) => ({ ...c, drive: true }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "フォルダ選択に失敗しました");
    } finally {
      setBusy(false);
    }
  };

  const allConnected = connected.drive && connected.calendar && connected.tasks;

  return (
    <div className="connect-sources">
      <ul className="connect-list">
        {SOURCES.map((s) => (
          <li key={s.key} className="connect-item">
            <span className="ci-icon">{s.icon}</span>
            <span className="ci-meta">
              <span className="ci-name">{s.name}</span>
              <span className="ci-desc">{s.desc}</span>
            </span>
            <span className={`ci-state ${connected[s.key] ? "on" : ""}`}>
              {connected[s.key] ? "✓ 連携済み" : "未連携"}
            </span>
          </li>
        ))}
      </ul>

      <button type="button" className="btn btn--gold btn--block" onClick={onConnect}>
        {allConnected ? "再連携する" : "Googleアカウントで連携する"}
      </button>

      {isPickerConfigured && (
        <div className="connect-picker">
          <button
            type="button"
            className="btn btn--ghost btn--block"
            onClick={onPickFolders}
            disabled={busy}
          >
            {busy ? "選択中…" : folders.length ? "Driveフォルダを選び直す" : "Driveの対象フォルダを選ぶ"}
          </button>
          {folders.length > 0 && (
            <ul className="connect-list" aria-label="選択したフォルダ">
              {folders.map((f) => (
                <li key={f.folderId} className="connect-item">
                  <span className="ci-icon">🗂️</span>
                  <span className="ci-meta">
                    <span className="ci-name">{f.name}</span>
                  </span>
                  <span className="ci-state on">対象</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="auth-note">⚠ {error}</p>}

      {!isFirebaseConfigured && (
        <p className="auth-note">※ デモモード（未ログイン）。ログインすると実際のGoogle連携になります。</p>
      )}
    </div>
  );
}
