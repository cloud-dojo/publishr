import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import BookCover from "../components/BookCover";
import ProgressBar from "../components/ProgressBar";
import { getBook, personaById } from "../data";
import styles from "./WritingPage.module.css";

type StepState = "done" | "active" | "wait";
interface Step {
  no: string;
  title: string;
  en: string;
  desc: string;
}
const STEPS: Step[] = [
  { no: "①", title: "観測", en: "Sense", desc: "指定フォルダ・カレンダー・タスクを観測" },
  { no: "②", title: "読者分析", en: "Reader Profile", desc: "3名のアナリストが状況を要約" },
  { no: "③", title: "企画会議", en: "Editorial Debate", desc: "3階層エージェントがスコアゲートで審議" },
  { no: "④", title: "著者の選出", en: "Casting", desc: "文体の重ならない著者を選定" },
  { no: "⑤", title: "執筆", en: "Writing", desc: "選ばれた著者が本文を書き下ろす" },
  { no: "⑥", title: "校正", en: "Editing", desc: "編集部が表現・構成を磨く" },
  { no: "⑦", title: "納本", en: "Delivery", desc: "あなたの書庫へ届ける" },
];

export default function WritingPage() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const book = getBook(bookId ?? "");
  const author = personaById(book.authorPersonaId);

  const [progress, setProgress] = useState(68);
  const [done, setDone] = useState(false);

  // 執筆進捗を擬似的に進める（writing → published）
  useEffect(() => {
    const t1 = setTimeout(() => setProgress(100), 1400);
    const t2 = setTimeout(() => setDone(true), 2600);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  const stepState = (i: number): StepState => {
    // ⑤執筆(index4)が進行中→完了で進む
    if (done) return i <= 6 ? "done" : "wait";
    if (i < 4) return "done";
    if (i === 4) return "active";
    return "wait";
  };

  return (
    <AppShell
      topBar={
        <>
          <button className={styles.back} onClick={() => navigate("/")}>
            ← あなたの書店にもどる
          </button>
          <span className={styles.bell}>🔔</span>
        </>
      }
    >
      <header className={styles.hero}>
        <span className="eyebrow">Now in the press</span>
        <h1 className={styles.title}>あなたの一冊を、執筆中です。</h1>
        <p className={styles.sub}>
          あなたが選んだ著者・専属の編集部が動き出しました。完成まで、企画の進む工程もお見せします。
        </p>
      </header>

      <div className={styles.body}>
        <div className={styles.coverCol}>
          <BookCover
            family={book.coverFamily}
            title={book.title}
            author={author?.name}
            size="lg"
          />
          <p className={styles.writingBy}>{author?.name} が執筆しています</p>
          <ProgressBar value={progress} />
        </div>

        <ol className={styles.steps}>
          {STEPS.map((s, i) => {
            const st = stepState(i);
            return (
              <li key={s.no} className={`${styles.step} ${styles[st]}`}>
                <span className={styles.stepMark}>
                  {st === "done" ? "✓" : st === "active" ? "◷" : "○"}
                </span>
                <div className={styles.stepBody}>
                  <span className={styles.stepTitle}>
                    {s.no} {s.title}
                    <span className={styles.stepEn}>{s.en}</span>
                  </span>
                  <span className={styles.stepDesc}>{s.desc}</span>
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      {done && (
        <div className={styles.banner}>
          <span className={styles.bannerIcon}>📖</span>
          <div className={styles.bannerText}>
            <span className={styles.bannerTitle}>
              「{book.title}」が入荷しました
            </span>
            <span className={styles.bannerSub}>
              {author?.name}・あなたのための書き下ろし
            </span>
          </div>
          <button
            className={styles.bannerBtn}
            onClick={() => navigate(`/reader/${book.bookId}`)}
          >
            いま読む →
          </button>
        </div>
      )}

      <footer className={styles.footer}>
        ※ UIモックアップ。工程・進捗はデモ用に擬似的に動作します（数秒で完成→入荷します）。
      </footer>
    </AppShell>
  );
}
