/*
 * Publishr ロゴマーク（A2：開いた本＋閃き／塗りのページ）。
 * ゴールド/ダークテーマ用。ワードマーク「Publishr」とは別部品。
 */
export default function Logo({
  size = 28,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      className={className}
      role="img"
      aria-label="Publishr"
    >
      {/* 閃き（四点星） */}
      <path
        d="M24 5 L25.44 7.56 L28 9 L25.44 10.44 L24 13 L22.56 10.44 L20 9 L22.56 7.56 Z"
        fill="#e3c389"
      />
      {/* 左ページ */}
      <path
        d="M24 23 C20 20, 13 19, 8 21.5 L8 37 C13 34.5, 20 35, 24 38 Z"
        fill="#c9a96a"
      />
      {/* 右ページ（陰） */}
      <path
        d="M24 23 C28 20, 35 19, 40 21.5 L40 37 C35 34.5, 28 35, 24 38 Z"
        fill="#b1934f"
      />
    </svg>
  );
}
