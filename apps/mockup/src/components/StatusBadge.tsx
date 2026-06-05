import type { BookStatus } from "../data/types";
import styles from "./StatusBadge.module.css";

const LABEL: Record<BookStatus, string> = {
  draft: "入荷",
  reserved: "予約中",
  writing: "執筆中",
  published: "既読",
};

export default function StatusBadge({ status }: { status: BookStatus }) {
  return (
    <span className={`${styles.badge} ${styles[status]}`}>{LABEL[status]}</span>
  );
}
