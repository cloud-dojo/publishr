import styles from "./SectionHeading.module.css";

interface Props {
  eyebrow?: string; // 英字アイブロウ "Today's arrival"
  title: string; // 和文見出し
  caption?: string; // 補足の一文
  action?: React.ReactNode; // 右端のリンク等
}

/* 英字アイブロウ + 和文見出しの2段組（全画面の統一見出し様式） */
export default function SectionHeading({ eyebrow, title, caption, action }: Props) {
  return (
    <div className={styles.wrap}>
      <div className={styles.texts}>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2 className={styles.title}>{title}</h2>
        {caption && <p className={styles.caption}>{caption}</p>}
      </div>
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
