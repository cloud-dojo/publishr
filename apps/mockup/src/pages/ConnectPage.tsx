import { useState } from "react";
import { useNavigate } from "react-router-dom";
import OnboardingFrame from "../components/OnboardingFrame";
import styles from "./ConnectPage.module.css";

const SOURCES = [
  {
    key: "drive",
    icon: "📁",
    name: "Google Drive",
    what: "業務資料・関心フォルダのテキスト",
    why: "いま何に取り組み、何に関心があるかを読み取ります。",
  },
  {
    key: "calendar",
    icon: "📅",
    name: "Google Calendar",
    what: "スケジュール・会議・役割の文脈",
    why: "業務の局面（会議過多・新任など）を推定します。",
  },
  {
    key: "tasks",
    icon: "✓",
    name: "Google Tasks",
    what: "タスクリスト・優先度の文脈",
    why: "いまの忙しさ・滞っている関心を捉えます。",
  },
];

export default function ConnectPage() {
  const navigate = useNavigate();
  const [connected, setConnected] = useState<Set<string>>(new Set());
  const allConnected = connected.size === SOURCES.length;

  const connect = () => {
    // モック: 連携を順次オンにする（実装では GET /api/auth/google/start → OAuth同意）
    SOURCES.forEach((s, i) => {
      setTimeout(() => {
        setConnected((prev) => new Set(prev).add(s.key));
      }, 350 * (i + 1));
    });
  };

  return (
    <OnboardingFrame wide>
      <div className={styles.head}>
        <span className="eyebrow">Connect your sources</span>
        <h1 className={styles.title}>観測するデータを、連携します。</h1>
        <p className={styles.caption}>
          Publishr は、あなたの3つのソースを週1回そっと観測し、企画に変えます。観測のみ・編集はしません。
        </p>
      </div>

      <ul className={styles.sources}>
        {SOURCES.map((s) => {
          const ok = connected.has(s.key);
          return (
            <li key={s.key} className={`${styles.source} ${ok ? styles.ok : ""}`}>
              <span className={styles.icon}>{s.icon}</span>
              <div className={styles.meta}>
                <span className={styles.name}>{s.name}</span>
                <span className={styles.what}>{s.what}</span>
                <span className={styles.why}>{s.why}</span>
              </div>
              <span className={`${styles.state} ${ok ? styles.stateOk : ""}`}>
                {ok ? "✓ 連携済み" : "未連携"}
              </span>
            </li>
          );
        })}
      </ul>

      <div className={styles.actions}>
        {!allConnected ? (
          <button className={styles.connectBtn} onClick={connect}>
            <span className={styles.gIcon} aria-hidden>
              G
            </span>
            Googleアカウントで連携する
          </button>
        ) : (
          <button className={styles.enterBtn} onClick={() => navigate("/")}>
            書店へ進む →
          </button>
        )}
        <button className={styles.later} onClick={() => navigate("/")}>
          あとで連携する
        </button>
      </div>

      <p className={styles.note}>
        ※ DEMO：実際の OAuth 同意画面（GET /api/auth/google/start）は未接続。ボタンで連携完了を擬似します。
      </p>
    </OnboardingFrame>
  );
}
