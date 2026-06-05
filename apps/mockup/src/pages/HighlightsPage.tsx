import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import SectionHeading from "../components/SectionHeading";
import FilterTabs from "../components/FilterTabs";
import type { TabDef } from "../components/FilterTabs";
import HighlightItem from "../components/HighlightItem";
import {
  highlights,
  getHighlightsByKind,
  getHighlightsGroupedByBook,
  getHighlightTagCloud,
  bookById,
} from "../data";
import type { HighlightKind } from "../data/types";
import styles from "./HighlightsPage.module.css";

type Tab = "all" | HighlightKind;

export default function HighlightsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("all");

  const tabs: TabDef[] = [
    { key: "all", label: "すべて", count: highlights.length },
    { key: "highlight", label: "ハイライト", count: getHighlightsByKind("highlight").length },
    { key: "note", label: "付箋", count: getHighlightsByKind("note").length },
    { key: "bookmark", label: "ブックマーク", count: getHighlightsByKind("bookmark").length },
  ];

  const groups = getHighlightsGroupedByBook(tab);
  const cloud = getHighlightTagCloud();

  return (
    <AppShell topBar={<span className={styles.crumb}>· あなたの書庫</span>}>
      <SectionHeading
        eyebrow="Your marks & margins"
        title="ハイライトと付箋"
        caption="あなたが線を引いた場所・付箋を貼った場所——これはあなたの関心の地図です。次に何を書くべきかを、Publishr はここから学びます。"
      />

      <FilterTabs
        tabs={tabs}
        active={tab}
        onChange={(k) => setTab(k as Tab)}
      />

      <div className={styles.layout}>
        <div className={styles.list}>
          {groups.map((g) => (
            <section key={g.bookId} className={styles.group}>
              <button
                className={styles.groupHead}
                onClick={() => navigate(`/book/${g.bookId}`)}
              >
                <span className={styles.groupTitle}>{g.bookTitle}</span>
                <span className={styles.groupCount}>{g.items.length}件</span>
              </button>
              <div className={styles.items}>
                {g.items.map((h) => (
                  <HighlightItem
                    key={h.id}
                    highlight={h}
                    onClick={() => navigate(`/reader/${h.bookId}`)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <aside className={styles.side}>
          <div className={styles.sideCard}>
            <h3 className={styles.sideTitle}>あなたの関心の地図</h3>
            <div className={styles.cloud}>
              {cloud.map((c) => (
                <span
                  key={c.tag}
                  className={styles.cloudTag}
                  style={{ fontSize: 12 + Math.min(c.count, 5) * 2 }}
                >
                  {c.tag}
                  <span className={styles.cloudCount}>{c.count}</span>
                </span>
              ))}
            </div>
          </div>

          <div className={styles.sideCard}>
            <h3 className={styles.sideTitle}>この関心が、次の企画に</h3>
            <p className={styles.sideNote}>
              「{cloud[0]?.tag}」「{cloud[1]?.tag}
              」へのマーキングが多いため、来週の企画は「
              {bookById("b_deleg")?.subtitle ?? "任せ方"}
              」方向に寄せています。
            </p>
          </div>
        </aside>
      </div>

      <footer className={styles.footer}>
        ★ HighlightItem クリックで該当の読書画面へ、書籍名クリックで本の詳細へ移動します。
      </footer>
    </AppShell>
  );
}
