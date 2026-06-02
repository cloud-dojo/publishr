import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ワークスペースの共有スキーマ（生TSをエクスポート）をトランスパイル
  transpilePackages: ["@publishr/shared-schema"],
};

export default nextConfig;
