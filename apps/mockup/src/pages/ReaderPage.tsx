import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import Stars from "../components/Stars";
import { getBook, personaById, bodySample } from "../data";
import { useFavorites, toggleFavorite } from "../data/favoritesStore";
import type { BodyBlock } from "../data/types";
import styles from "./ReaderPage.module.css";

const REACTIONS = [
  { key: "useful", label: "まず役に立った", icon: "★" },
  { key: "ref", label: "参考になった", icon: "✎" },
  { key: "hard", label: "難しかった", icon: "△" },
  { key: "later", label: "後で読み返す", icon: "⤴" },
];

const FONT_SIZES = [15, 17, 19];

/* {{...}} をハイライトspanに変換 */
function renderText(text: string) {
  const parts = text.split(/(\{\{.*?\}\})/g);
  return parts.map((p, i) =>
    p.startsWith("{{") && p.endsWith("}}") ? (
      <mark key={i} className={styles.hl}>
        {p.slice(2, -2)}
      </mark>
    ) : (
      <span key={i}>{p}</span>
    )
  );
}

function Block({ block }: { block: BodyBlock }) {
  if (block.type === "dropcap") {
    const first = block.text[0];
    const rest = block.text.slice(1);
    return (
      <p className={styles.para}>
        <span className={styles.dropcap}>{first}</span>
        {rest}
      </p>
    );
  }
  if (block.type === "note") {
    return <aside className={styles.inlineNote}>{block.text}</aside>;
  }
  return <p className={styles.para}>{renderText(block.text)}</p>;
}

export default function ReaderPage() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const book = getBook(bookId ?? "");
  const author = personaById(book.authorPersonaId);
  const body = bodySample;

  const [fontIdx, setFontIdx] = useState(1);
  const [reaction, setReaction] = useState<string | null>("useful");
  const [rating, setRating] = useState(book.feedback?.rating ?? 0);
  const favorites = useFavorites();
  const isFav = author ? favorites.has(author.personaId) : false;

  return (
    <AppShell
      variant="reader"
      topBar={
        <>
          <span className={styles.crumb}>
            <button onClick={() => navigate("/library")}>書庫</button>
            <span className={styles.sep}>›</span>
            <button onClick={() => navigate(`/book/${book.bookId}`)}>
              {book.title}
            </button>
            <span className={styles.sep}>›</span>
            <span className={styles.crumbAuthor}>{author?.name}</span>
          </span>
          <div className={styles.viewTools}>
            <button className={styles.tool}>フル</button>
            <button className={`${styles.tool} ${styles.toolOn}`}>標準</button>
            <button
              className={styles.tool}
              onClick={() => setFontIdx((i) => (i + 1) % FONT_SIZES.length)}
            >
              Aa
            </button>
          </div>
        </>
      }
      rightPanel={
        <div className={styles.panel}>
          <PanelSection title="このページの作業">
            <div className={styles.actions}>
              <button className={styles.action}>✎ ハイライト</button>
              <button className={styles.action}>❏ 付箋を貼る</button>
            </div>
            <p className={styles.hint}>
              本文を選択すると、ハイライト／付箋を追加できます（モックでは固定表示）。
            </p>
            <button
              className={`${styles.favBtn} ${isFav ? styles.favOn : ""}`}
              onClick={() => author && toggleFavorite(author.personaId)}
            >
              {isFav
                ? `★ ${author?.name} をお気に入り登録済み`
                : `☆ この作家をお気に入り登録`}
            </button>
          </PanelSection>

          <PanelSection title="読みながら、ひとこと">
            <div className={styles.reactions}>
              {REACTIONS.map((r) => (
                <button
                  key={r.key}
                  className={`${styles.reaction} ${
                    reaction === r.key ? styles.reactionOn : ""
                  }`}
                  onClick={() => setReaction(r.key)}
                >
                  <span className={styles.reactionIcon}>{r.icon}</span>
                  {r.label}
                </button>
              ))}
            </div>
          </PanelSection>

          <PanelSection title="このページのしるし">
            <div className={styles.ratingRow}>
              <Stars value={rating} onChange={setRating} size={20} />
              <span className={styles.ratingHint}>
                {rating > 0 ? `${rating} / 5` : "評価する"}
              </span>
            </div>
            <button
              className={styles.finishBtn}
              onClick={() => navigate(`/author/${author?.personaId}`)}
            >
              読了する →
            </button>
          </PanelSection>
        </div>
      }
    >
      <article className={styles.reader} style={{ fontSize: FONT_SIZES[fontIdx] }}>
        <span className={styles.chapterLabel}>{body.chapterLabel}</span>
        <h1 className={styles.chapterTitle}>{body.chapterTitle}</h1>
        <div className={styles.bodyText}>
          {body.blocks.map((b, i) => (
            <Block key={i} block={b} />
          ))}
        </div>
        <div className={styles.pageFooter}>
          43% · 残り 14 分
        </div>
      </article>
    </AppShell>
  );
}

function PanelSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className={styles.panelSection}>
      <h3 className={styles.panelTitle}>{title}</h3>
      {children}
    </section>
  );
}
