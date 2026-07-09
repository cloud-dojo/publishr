import type { ReactNode } from "react";
import Sidebar from "./Sidebar";
import styles from "./AppShell.module.css";

interface Props {
  children: ReactNode;
  rightPanel?: ReactNode; // 読書画面のみ（280px）
  topBar?: ReactNode; // ブレッドクラム・検索などのページ上部バー
  variant?: "default" | "reader";
}

/*
 * 全画面共通レイアウト。grid: 240px 1fr [280px]。
 * rightPanel 指定時のみ右パネルを表示（読書画面 §3-9）。
 */
export default function AppShell({
  children,
  rightPanel,
  topBar,
  variant = "default",
}: Props) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.main}>
        {topBar && <div className={styles.topBar}>{topBar}</div>}
        <div
          className={`${styles.content} ${
            variant === "reader" ? styles.readerContent : ""
          }`}
        >
          {children}
        </div>
      </main>
      {rightPanel && <div className={styles.rightPanel}>{rightPanel}</div>}
    </div>
  );
}
