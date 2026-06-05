import type { Highlight } from "../data/types";
import styles from "./HighlightItem.module.css";

const KIND_LABEL: Record<string, string> = {
  highlight: "ハイライト",
  note: "付箋",
  bookmark: "ブックマーク",
};

export default function HighlightItem({
  highlight,
  onClick,
}: {
  highlight: Highlight;
  onClick?: () => void;
}) {
  const { kind, text, chapter, note, tags } = highlight;
  return (
    <article
      className={`${styles.item} ${styles[kind]}`}
      onClick={onClick}
    >
      <div className={styles.head}>
        <span className={`${styles.kind} ${styles[`k_${kind}`]}`}>
          {KIND_LABEL[kind]}
        </span>
        {chapter && <span className={styles.chapter}>{chapter}</span>}
      </div>
      <p className={styles.text}>{text}</p>
      {note && <p className={styles.noteBox}>{note}</p>}
      {tags.length > 0 && (
        <div className={styles.tags}>
          {tags.map((t) => (
            <span key={t} className={styles.tag}>
              #{t}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
