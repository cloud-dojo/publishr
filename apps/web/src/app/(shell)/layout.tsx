import { AuthGate } from "@/components/AuthGate";
import { AuthSync } from "@/components/AuthSync";
import { Sidebar } from "@/components/shell/Sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    // AuthGate: 認証確定まで描画を止め、未認証は /login へ（佐倉/ゲストのフラッシュ防止・旧 AuthGuard を統合）。
    <AuthGate>
      <div className="app">
        {/* Firebase Auth → FirestoreProvider.setOwnerUid() の橋渡し */}
        <AuthSync />
        <Sidebar />
        <main className="main">{children}</main>
      </div>
    </AuthGate>
  );
}
