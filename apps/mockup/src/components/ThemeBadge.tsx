import type { ThemeKind } from "../data/types";
import styles from "./ThemeBadge.module.css";

const LABEL: Record<ThemeKind, string> = {
  honmei: "関心",
  serendipity: "新しい出会い",
};

/* 本の種別タグ（関心 / 新しい出会い）。StatusBadge と同じpill様式 */
export default function ThemeBadge({ kind }: { kind: ThemeKind }) {
  return (
    <span className={`${styles.badge} ${styles[kind]}`}>{LABEL[kind]}</span>
  );
}

export const themeKindLabel = (kind: ThemeKind) => LABEL[kind];
