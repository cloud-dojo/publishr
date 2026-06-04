import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import BookCover from "../components/BookCover";
import StatusBadge from "../components/StatusBadge";
import ThemeBadge from "../components/ThemeBadge";
import { getBook, getPlan, personaById } from "../data";
import styles from "./BookDetailPage.module.css";

export default function BookDetailPage() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const book = getBook(bookId ?? "");
  const plan = getPlan(book.planId);
  const mainAuthor = personaById(book.authorPersonaId);
  const [agendaTab, setAgendaTab] = useState<"agenda" | "preface">("agenda");

  const reserve = () => {
    // モック: 予約 → 執筆中通知へ（実装では POST /api/reserve）
    navigate(`/writing/${book.bookId}`);
  };

  return (
    <AppShell
      topBar={
        <>
          <span className={styles.eyebrowTop}>
            Today's arrival — carved for you
          </span>
          <button className={styles.backLink} onClick={() => navigate("/")}>
            ← 書店へ戻る
          </button>
        </>
      }
    >
      <div className={styles.top}>
        {/* 左: 表紙 + 企画コンテキスト */}
        <div className={styles.left}>
          <BookCover
            family={book.coverFamily}
            title={book.title}
            author={mainAuthor?.name}
            size="lg"
          />
          <button
            className={styles.cover2author}
            onClick={() => navigate(`/author/${mainAuthor?.personaId}`)}
          >
            著者 {mainAuthor?.name} を見る →
          </button>
        </div>

        <div className={styles.context}>
          <div className={styles.titleRow}>
            <ThemeBadge kind={book.themeKind} />
            <StatusBadge status={book.status} />
          </div>
          <h1 className={styles.title}>{book.title}</h1>
          {book.subtitle && <p className={styles.subtitle}>{book.subtitle}</p>}

          {plan && (
            <dl className={styles.ctxList}>
              <Row label="今、あなたは" value={plan.reason} />
              <Row label="解決する課題" value={plan.readerSituation} />
              <Row label="核心メッセージ" value={plan.coreMessage} highlight />
            </dl>
          )}

          <button className={styles.cta} onClick={reserve}>
            この本を予約する →
          </button>
          <span className={styles.ctaNote}>
            {mainAuthor?.name} が、あなたのために書き下ろします。
          </span>
        </div>
      </div>

      {/* アジェンダ + 序文サンプル */}
      <section className={styles.agendaSection}>
        <div className={styles.agendaTabs}>
          <button
            className={agendaTab === "agenda" ? styles.tabOn : styles.tab}
            onClick={() => setAgendaTab("agenda")}
          >
            アジェンダ（目次）
          </button>
          <button
            className={agendaTab === "preface" ? styles.tabOn : styles.tab}
            onClick={() => setAgendaTab("preface")}
          >
            序文サンプル
          </button>
        </div>

        {agendaTab === "agenda" ? (
          <ol className={styles.agenda}>
            {plan?.agendaOutline.map((a) => (
              <li key={a.no} className={styles.agendaItem}>
                <span className={styles.agendaNo}>{a.no}</span>
                <div>
                  <span className={styles.agendaTitle}>{a.title}</span>
                  {a.note && <span className={styles.agendaNote}>{a.note}</span>}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className={styles.preface}>{book.prefaceSample}</p>
        )}
      </section>

      <footer className={styles.footer}>
        ※ この本は {mainAuthor?.name}{" "}
        が企画・執筆します。予約すると執筆が始まり、完成後に書庫へ届きます（デモ）。
      </footer>
    </AppShell>
  );
}

function Row({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={styles.row}>
      <dt className={styles.rowLabel}>{label}</dt>
      <dd className={`${styles.rowValue} ${highlight ? styles.rowHi : ""}`}>
        {value}
      </dd>
    </div>
  );
}
