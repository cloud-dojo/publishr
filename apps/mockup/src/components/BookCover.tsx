import type { CoverFamily } from "../data/types";
import styles from "./BookCover.module.css";

type Size = "sm" | "md" | "lg" | "spine";

interface Props {
  family: CoverFamily;
  title: string;
  author?: string;
  size?: Size;
}

/*
 * 表紙を CSS グラデで描画（画像不要）。上端の金ライン・左の背表紙帯・タイトルオーバーレイ。
 * family は theme.css の --cover-*-top/bottom を参照。
 */
export default function BookCover({ family, title, author, size = "md" }: Props) {
  return (
    <div
      className={`${styles.cover} ${styles[size]} ${styles[`fam_${family}`]}`}
      role="img"
      aria-label={`${title}${author ? ` / ${author}` : ""}`}
    >
      <span className={styles.spine} />
      <span className={styles.gild} />
      {size !== "spine" && (
        <div className={styles.overlay}>
          <span className={styles.title}>{title}</span>
          {author && <span className={styles.author}>{author}</span>}
        </div>
      )}
    </div>
  );
}
