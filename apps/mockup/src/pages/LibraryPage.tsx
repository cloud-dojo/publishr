import { useState } from "react";
import AppShell from "../components/AppShell";
import SectionHeading from "../components/SectionHeading";
import BookCard from "../components/BookCard";
import FilterTabs from "../components/FilterTabs";
import type { TabDef } from "../components/FilterTabs";
import { getLibraryBooks, getLibraryStats } from "../data";
import type { Book } from "../data/types";
import styles from "./LibraryPage.module.css";

const TABS: TabDef[] = [
  { key: "all", label: "すべて" },
  { key: "reading", label: "読書中" },
  { key: "published", label: "読了" },
  { key: "reserved", label: "予約中" },
  { key: "honmei", label: "関心" },
  { key: "serendipity", label: "新しい出会い" },
];

function match(book: Book, tab: string): boolean {
  switch (tab) {
    case "all":
      return true;
    case "reading":
      return book.status === "writing" || (book.feedback?.read ?? 0) > 0 && (book.feedback?.read ?? 0) < 100;
    case "published":
      return book.status === "published";
    case "reserved":
      return book.status === "reserved";
    case "honmei":
      return book.themeKind === "honmei";
    case "serendipity":
      return book.themeKind === "serendipity";
    default:
      return true;
  }
}

export default function LibraryPage() {
  const [tab, setTab] = useState("all");
  const stats = getLibraryStats();
  const books = getLibraryBooks().filter((b) => match(b, tab));

  const tabsWithCount = TABS.map((t) => ({
    ...t,
    count: getLibraryBooks().filter((b) => match(b, t.key)).length,
  }));

  return (
    <AppShell
      topBar={<span className={styles.crumb}>· あなたの書庫</span>}
    >
      <SectionHeading
        eyebrow="Your growing library"
        title="わたしの書庫"
        caption="あなたのために書かれた本が、ここに増えていきます。読むほど、Publishr はあなたを深く理解します。"
      />

      <div className={styles.stats}>
        <Stat n={stats.total} label="冊 所蔵" />
        <Stat n={stats.finished} label="冊 読了" />
        <Stat n={stats.avgRating} label="平均評価" suffix="点" />
        <Stat n={stats.highlightCount} label="ハイライト" />
      </div>

      <FilterTabs tabs={tabsWithCount} active={tab} onChange={setTab} />

      <div className={styles.grid}>
        {books.map((b) => (
          <BookCard key={b.bookId} book={b} />
        ))}
      </div>

      <footer className={styles.footer}>
        ★ 棚はあなたの足あと。読了・評価・ハイライトがすべて次の企画に効きます。
      </footer>
    </AppShell>
  );
}

function Stat({
  n,
  label,
  suffix,
}: {
  n: number;
  label: string;
  suffix?: string;
}) {
  return (
    <div className={styles.stat}>
      <span className={styles.statNum}>
        {n}
        {suffix && <span className={styles.statSuffix}>{suffix}</span>}
      </span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
