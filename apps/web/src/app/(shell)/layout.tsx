import { AuthGuard } from "@/components/AuthGuard";
import { AuthSync } from "@/components/AuthSync";
import { Sidebar } from "@/components/shell/Sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      {/* 未認証なら /login へ（Firebase設定時のみ作動・mockは無効） */}
      <AuthGuard />
      {/* Firebase Auth → FirestoreProvider.setOwnerUid() の橋渡し */}
      <AuthSync />
      <Sidebar />
      <main className="main">{children}</main>
    </div>
  );
}
