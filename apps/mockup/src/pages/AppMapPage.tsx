import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { books } from "../data";
import styles from "./AppMapPage.module.css";

const FLOW = [
  { en: "Sense", ja: "観測", desc: "Drive・Calendar・Tasks を週1回観測" },
  { en: "Deliberate", ja: "企画判断", desc: "3階層エージェント会議→スコアゲート" },
  { en: "Publish", ja: "出版", desc: "著者を選び、本文を書き下ろす" },
  { en: "Learn", ja: "学習", desc: "ハイライト・FB・お気に入りが次へ反映" },
];

const CARDS = [
  { group: "はじめる", to: "/login", icon: "🔑", title: "ログイン", desc: "Googleでログイン。初回は登録へ進む。" },
  { group: "はじめる", to: "/onboarding", icon: "📝", title: "初期登録", desc: "業界・職種・関心をタップで登録（5問）。" },
  { group: "はじめる", to: "/connect", icon: "🔗", title: "データ連携", desc: "Drive・Calendar・Tasks の観測に同意。" },
  { group: "届く", to: "/", icon: "▣", title: "書店トップ", desc: "今朝の入荷。なぜこの本かを添えて並ぶ。" },
  { group: "選ぶ・作る", to: "/book/b_deleg", icon: "📖", title: "本の詳細", desc: "企画情報・序文・著者5人を比較して予約。" },
  { group: "選ぶ・作る", to: "/writing/b_deleg", icon: "✍", title: "執筆中・入荷通知", desc: "進捗68%→完成。工程をリアルタイム表示。" },
  { group: "読む・育つ", to: "/reader/b_deleg", icon: "📚", title: "読書（Kindle風）", desc: "本文・ハイライト・付箋・★評価。" },
  { group: "読む・育つ", to: "/library", icon: "▤", title: "わたしの書庫", desc: "読了・予約・統計を横断。棚が育つ。" },
  { group: "読む・育つ", to: "/highlights", icon: "❏", title: "ハイライト・付箋", desc: "線を引いた場所＝関心の地図。" },
  { group: "読む・育つ", to: "/authors", icon: "✒", title: "作家たち", desc: "作家の紹介・名言・お気に入り登録。" },
];

export default function AppMapPage() {
  const navigate = useNavigate();
  const groups = [...new Set(CARDS.map((c) => c.group))];

  return (
    <AppShell topBar={<span className={styles.crumb}>· あなたの書店</span>}>
      <header className={styles.hero}>
        <span className="eyebrow">The map of the experience</span>
        <h1 className={styles.title}>Publishr 体験の地図</h1>
        <p className={styles.sub}>
          すべての画面は、ひとつの記憶ループにあります。各画面が翌週の企画を更新します。
        </p>
      </header>

      <div className={styles.flow}>
        {FLOW.map((f, i) => (
          <div key={f.en} className={styles.flowItem}>
            <span className={styles.flowEn}>{f.en}</span>
            <span className={styles.flowJa}>{f.ja}</span>
            <span className={styles.flowDesc}>{f.desc}</span>
            {i < FLOW.length - 1 && <span className={styles.arrow}>→</span>}
          </div>
        ))}
      </div>

      {groups.map((g) => (
        <section key={g} className={styles.section}>
          <span className={styles.groupLabel}>{g}</span>
          <div className={styles.cards}>
            {CARDS.filter((c) => c.group === g).map((c) => (
              <button
                key={c.title}
                className={styles.card}
                onClick={() => navigate(c.to)}
              >
                <span className={styles.cardIcon}>{c.icon}</span>
                <span className={styles.cardTitle}>{c.title}</span>
                <span className={styles.cardDesc}>{c.desc}</span>
                <span className={styles.cardGo}>開く →</span>
              </button>
            ))}
          </div>
        </section>
      ))}

      <footer className={styles.footer}>
        ※ 全{books.length}冊・モックアップ（ダミーデータ）。各カードから対応画面へ移動できます。
      </footer>
    </AppShell>
  );
}
