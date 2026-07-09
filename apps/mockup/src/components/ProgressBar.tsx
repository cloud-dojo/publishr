import styles from "./ProgressBar.module.css";

export default function ProgressBar({
  value,
  label,
}: {
  value: number; // 0-100
  label?: string;
}) {
  return (
    <div className={styles.wrap}>
      {label && (
        <div className={styles.head}>
          <span className={styles.label}>{label}</span>
          <span className={styles.pct}>{Math.round(value)}%</span>
        </div>
      )}
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
