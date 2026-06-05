import { useNavigate } from "react-router-dom";
import type { Persona } from "../data/types";
import styles from "./AuthorChip.module.css";

interface Props {
  persona: Persona;
  isFavorite?: boolean;
  onToggleFav?: () => void;
  variant?: "select" | "compact"; // select=著者選択カード / compact=小
  prefaceSample?: string; // 著者選択時の序文出だし
  onSelect?: () => void; // 「この著者版を予約する」
}

export default function AuthorChip({
  persona,
  isFavorite,
  onToggleFav,
  variant = "compact",
  prefaceSample,
  onSelect,
}: Props) {
  const navigate = useNavigate();

  if (variant === "compact") {
    return (
      <button
        className={styles.compact}
        onClick={() => navigate(`/author/${persona.personaId}`)}
      >
        <span className={styles.avatar}>{persona.avatarChar}</span>
        <span className={styles.compactMeta}>
          <span className={styles.name}>{persona.name}</span>
          <span className={styles.style}>{persona.style}</span>
        </span>
        {onToggleFav && (
          <span
            className={`${styles.fav} ${isFavorite ? styles.favOn : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleFav();
            }}
          >
            {isFavorite ? "★" : "☆"}
          </span>
        )}
      </button>
    );
  }

  return (
    <article className={styles.selectCard}>
      <header
        className={styles.selectHead}
        onClick={() => navigate(`/author/${persona.personaId}`)}
      >
        <span className={styles.avatar}>{persona.avatarChar}</span>
        <div>
          <span className={styles.name}>{persona.name}</span>
          <div className={styles.tags}>
            {persona.styleTags.map((t) => (
              <span key={t} className={styles.tag}>
                {t}
              </span>
            ))}
          </div>
        </div>
      </header>
      <p className={styles.voice}>{persona.voice}</p>
      {prefaceSample && <p className={styles.preface}>{prefaceSample}</p>}
      <button className={styles.selectBtn} onClick={onSelect}>
        この著者版を予約する
      </button>
    </article>
  );
}
