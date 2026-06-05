import styles from "./Stars.module.css";

/* ★評価の表示（読み取り専用 or クリック可） */
export default function Stars({
  value = 0,
  onChange,
  size = 14,
}: {
  value?: number;
  onChange?: (v: number) => void;
  size?: number;
}) {
  return (
    <span className={styles.stars} style={{ fontSize: size }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={`${styles.star} ${n <= Math.round(value) ? styles.on : ""} ${
            onChange ? styles.clickable : ""
          }`}
          onClick={onChange ? () => onChange(n) : undefined}
        >
          {n <= Math.round(value) ? "★" : "☆"}
        </span>
      ))}
    </span>
  );
}
