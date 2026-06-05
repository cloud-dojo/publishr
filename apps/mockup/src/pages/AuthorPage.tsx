import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import BookCard from "../components/BookCard";
import { personaById, personas, getBooksByAuthor, highlights } from "../data";
import { useFavorites, toggleFavorite } from "../data/favoritesStore";
import styles from "./AuthorPage.module.css";

export default function AuthorPage() {
  const { personaId } = useParams();
  const navigate = useNavigate();
  const persona = personaById(personaId ?? "") ?? personas[0];

  const favorites = useFavorites();
  const fav = favorites.has(persona.personaId);
  const [toast, setToast] = useState(false);

  const books = getBooksByAuthor(persona.personaId);
  const hlCount = highlights.filter((h) =>
    books.some((b) => b.bookId === h.bookId)
  ).length;

  const onToggleFav = () => {
    const nowFav = toggleFavorite(persona.personaId);
    if (nowFav) {
      setToast(true);
      setTimeout(() => setToast(false), 3200);
    }
  };

  return (
    <AppShell
      topBar={
        <span className={styles.crumb}>
          <button onClick={() => navigate("/library")}>あなたの書庫</button>
          <span className={styles.sep}>›</span>
          <span>著者プロフィール</span>
        </span>
      }
    >
      <header className={styles.header}>
        <span className={styles.avatar}>{persona.avatarChar}</span>
        <div className={styles.headMeta}>
          <span className="eyebrow">Your dedicated author</span>
          <h1 className={styles.name}>{persona.name}</h1>
          <div className={styles.tags}>
            {persona.styleTags.map((t) => (
              <span key={t} className={styles.tag}>
                {t}
              </span>
            ))}
          </div>
          <div className={styles.headActions}>
            <button
              className={`${styles.favBtn} ${fav ? styles.favOn : ""}`}
              onClick={onToggleFav}
            >
              {fav ? "★ お気に入り登録済み" : "☆ お気に入りの作家に登録"}
            </button>
            <span className={styles.counts}>
              この著者の本 {books.length}冊 ・ ハイライト {hlCount}個
            </span>
          </div>
        </div>
      </header>

      <section className={styles.persona}>
        <span className="eyebrow">Introduction</span>
        <h2 className={styles.sectionTitle}>この作家の紹介</h2>
        <div className={styles.personaGrid}>
          <PersonaCard en="Background" title="背景" text={persona.background} />
          <PersonaCard en="Voice" title="文体" text={persona.voice} />
          <PersonaCard en="Thought" title="思想" text={persona.thought} />
          <PersonaCard
            en="Expertise"
            title="専門・テーマ"
            chips={persona.expertise}
          />
        </div>
      </section>

      <blockquote className={styles.quote}>
        <span className={styles.quoteMark}>“</span>
        {persona.quote}
      </blockquote>

      <section className={styles.books}>
        <span className="eyebrow">Books for you</span>
        <h2 className={styles.sectionTitle}>あなたに——この著者の本</h2>
        {books.length > 0 ? (
          <div className={styles.bookGrid}>
            {books.slice(0, 3).map((b) => (
              <BookCard key={b.bookId} book={b} />
            ))}
          </div>
        ) : (
          <p className={styles.empty}>
            この著者の本は、まだあなたの棚にありません。
          </p>
        )}
      </section>

      <div className={styles.bottomCta}>
        <button className={styles.nextBtn} onClick={() => navigate("/")}>
          次の本を選ぶ →
        </button>
      </div>

      {toast && (
        <div className={styles.toast}>
          お気に入りに登録しました。この著者が、これからもあなたのために書き続けます。
        </div>
      )}
    </AppShell>
  );
}

function PersonaCard({
  en,
  title,
  text,
  chips,
}: {
  en: string;
  title: string;
  text?: string;
  chips?: string[];
}) {
  return (
    <article className={styles.pCard}>
      <span className={styles.pEn}>{en}</span>
      <h3 className={styles.pTitle}>{title}</h3>
      {text && <p className={styles.pText}>{text}</p>}
      {chips && (
        <div className={styles.pChips}>
          {chips.map((c) => (
            <span key={c} className={styles.pChip}>
              {c}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
