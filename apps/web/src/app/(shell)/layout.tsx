"use client";

import { usePathname } from "next/navigation";

import { AuthGuard } from "@/components/AuthGuard";
import { AuthSync } from "@/components/AuthSync";
import { NavigationHistoryTracker } from "@/components/shell/NavigationHistory";
import { Sidebar } from "@/components/shell/Sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const readerMode = /^\/read\/[^/]+$/.test(pathname ?? "");

  return (
    <div className={`app${readerMode ? " app--reader" : ""}`}>
      {/* 未認証なら /login へ（Firebase設定時のみ作動・mockは無効） */}
      <AuthGuard />
      {/* Firebase Auth → FirestoreProvider.setOwnerUid() の橋渡し */}
      <AuthSync />
      <NavigationHistoryTracker />
      {!readerMode ? <Sidebar /> : null}
      <main className="main">{children}</main>
    </div>
  );
}
