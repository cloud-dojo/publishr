import type { Metadata } from "next";

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
      <body>{children}</body>
    </html>
  );
}
