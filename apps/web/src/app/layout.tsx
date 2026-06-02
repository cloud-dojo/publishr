import type { Metadata } from "next";

import { Sidebar } from "@/components/shell/Sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Publishr — あなたの書店",
  description: "あなた専属の、AI出版社。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body>
        <div className="app">
          <Sidebar />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
