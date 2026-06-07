import { AuthSync } from "@/components/AuthSync";
import { Sidebar } from "@/components/shell/Sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      {/* Firebase Auth → FirestoreProvider.setOwnerUid() の橋渡し */}
      <AuthSync />
      <Sidebar />
      <main className="main">{children}</main>
    </div>
  );
}
