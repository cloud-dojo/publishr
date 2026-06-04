import AppShell from "../components/AppShell";
import SectionHeading from "../components/SectionHeading";
import BookCard from "../components/BookCard";
import { getBooksByStatus, planById } from "../data";
import styles from "./StorefrontPage.module.css";

export default function StorefrontPage() {
  const arrivals = getBooksByStatus("draft");
  const reserved = getBooksByStatus("reserved");
  const forYou = arrivals.filter((b) => b.themeKind === "honmei");
  const newEncounters = arrivals.filter((b) => b.themeKind === "serendipity");

  return (
    <AppShell
      topBar={
        <>
          <span className={styles.topEyebrow}>
            木曜 · あなたの書店 — for you
          </span>
          <div className={styles.search}>本・著者・テーマで探す</div>
        </>
      }
    >
      <header className={styles.hero}>
        <span className="eyebrow">This morning's arrivals</span>
        <h1 className={styles.heroTitle}>
          今朝、あなたの書店に
          <br />
          新しい本が並びました。
        </h1>
        <p className={styles.heroSub}>
          佐倉さんの今週の状況を観測し、専属の編集部が選び、書き下ろした一冊たちです。
        </p>
      </header>

      <section className={styles.block}>
        <SectionHeading eyebrow="Curated for you this week" title="今週の入荷" />

        <div className={styles.group}>
          <div className={styles.groupHead}>
            <span className={styles.groupTitle}>いま、あなたの関心に</span>
            <span className={styles.groupCount}>{forYou.length}冊</span>
            <span className={styles.groupNote}>
              観測したいまの状況に、まっすぐ応える本
            </span>
          </div>
          <div className={styles.arrivalGrid}>
            {forYou.map((b) => (
              <BookCard
                key={b.bookId}
                book={b}
                plan={planById(b.planId)}
                showReason
                showStatus={false}
                showThemeBadge
              />
            ))}
          </div>
        </div>

        <div className={styles.group}>
          <div className={styles.groupHead}>
            <span className={styles.groupTitle}>新しい出会い</span>
            <span className={styles.groupCount}>{newEncounters.length}冊</span>
            <span className={styles.groupNote}>
              関心の少し外側から、視野を広げる本
            </span>
          </div>
          <div className={styles.arrivalGrid}>
            {newEncounters.map((b) => (
              <BookCard
                key={b.bookId}
                book={b}
                plan={planById(b.planId)}
                showReason
                showStatus={false}
                showThemeBadge
              />
            ))}
          </div>
        </div>
      </section>

      <section className={styles.block}>
        <SectionHeading eyebrow="On hold" title="予約中" />
        <div className={styles.grid}>
          {reserved.map((b) => (
            <BookCard key={b.bookId} book={b} />
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        ※ AIエージェント（Publishr）が Drive・Calendar・Tasks
        を観測し、企画・著者選定・執筆まで自律的に行っています。これはデモ用のダミーデータです。
      </footer>
    </AppShell>
  );
}
