import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import SectionHeading from "../components/SectionHeading";
import { user, getLibraryStats } from "../data";
import { useFavorites } from "../data/favoritesStore";
import { profileSteps } from "../data/profileOptions";
import styles from "./AccountPage.module.css";

const interestOptions =
  profileSteps.find((s) => s.key === "recentInterests")?.options ?? [];
const genreOptions =
  profileSteps.find((s) => s.key === "readingGenres")?.options ?? [];

const CONNECTED = [
  { name: "Google Drive", icon: "📁" },
  { name: "Google Calendar", icon: "📅" },
  { name: "Google Tasks", icon: "✓" },
];

export default function AccountPage() {
  const navigate = useNavigate();
  const favorites = useFavorites();
  const stats = getLibraryStats();

  const [interests, setInterests] = useState<string[]>(
    user.initialProfile.recentInterests
  );
  const [genres, setGenres] = useState<string[]>(
    user.initialProfile.readingGenres
  );
  const [dirty, setDirty] = useState(false);
  const [toast, setToast] = useState(false);

  const toggle = (
    list: string[],
    set: (v: string[]) => void,
    opt: string
  ) => {
    set(list.includes(opt) ? list.filter((o) => o !== opt) : [...list, opt]);
    setDirty(true);
  };

  const save = () => {
    // 実装では users/{uid}.initialProfile を直書き更新
    setDirty(false);
    setToast(true);
    setTimeout(() => setToast(false), 2800);
  };

  return (
    <AppShell topBar={<span className={styles.crumb}>· アカウント</span>}>
      <header className={styles.header}>
        <span className={styles.avatar}>{user.avatarChar}</span>
        <div className={styles.headMeta}>
          <span className="eyebrow">Your account</span>
          <h1 className={styles.name}>{user.displayName}</h1>
          <span className={styles.email}>{user.email}</span>
        </div>
        <div className={styles.miniStats}>
          <Mini n={stats.total} label="冊" />
          <Mini n={stats.highlightCount} label="ハイライト" />
          <Mini n={favorites.size} label="お気に入り作家" />
        </div>
      </header>

      {/* 登録情報（読み取り） */}
      <section className={styles.section}>
        <SectionHeading eyebrow="Registered profile" title="登録情報" />
        <div className={styles.infoGrid}>
          <Info label="業界" value={user.initialProfile.industry} />
          <Info label="職種" value={user.initialProfile.jobType} />
          <Info label="役職" value={user.initialProfile.position} />
        </div>
        <p className={styles.infoNote}>
          業界・職種・役職は初回登録時の値です。変更が必要な場合はサポートまで（MVPでは編集不可）。
        </p>
      </section>

      {/* 関心（編集可） */}
      <section className={styles.section}>
        <SectionHeading
          eyebrow="Your interests"
          title="いまの関心"
          caption="ここを更新すると、来週の企画の方向が変わります。"
        />
        <div className={styles.chips}>
          {interestOptions.map((opt) => (
            <button
              key={opt}
              className={`${styles.chip} ${
                interests.includes(opt) ? styles.on : ""
              }`}
              onClick={() => toggle(interests, setInterests, opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </section>

      {/* 読書傾向（編集可） */}
      <section className={styles.section}>
        <SectionHeading eyebrow="Reading taste" title="読書傾向" />
        <div className={styles.chips}>
          {genreOptions.map((opt) => (
            <button
              key={opt}
              className={`${styles.chip} ${
                genres.includes(opt) ? styles.on : ""
              }`}
              onClick={() => toggle(genres, setGenres, opt)}
            >
              {opt}
            </button>
          ))}
        </div>
        <div className={styles.saveRow}>
          <button className={styles.save} onClick={save} disabled={!dirty}>
            {dirty ? "変更を保存する" : "保存済み"}
          </button>
        </div>
      </section>

      {/* データ連携 */}
      <section className={styles.section}>
        <SectionHeading
          eyebrow="Connected sources"
          title="データ連携"
          action={
            <button
              className={styles.manageLink}
              onClick={() => navigate("/connect")}
            >
              連携を管理 →
            </button>
          }
        />
        <ul className={styles.sources}>
          {CONNECTED.map((s) => (
            <li key={s.name} className={styles.source}>
              <span className={styles.sourceIcon}>{s.icon}</span>
              <span className={styles.sourceName}>{s.name}</span>
              <span className={styles.sourceState}>✓ 連携済み</span>
            </li>
          ))}
        </ul>
      </section>

      <div className={styles.bottom}>
        <button className={styles.logout} onClick={() => navigate("/login")}>
          ログアウト
        </button>
      </div>

      {toast && (
        <div className={styles.toast}>
          関心を更新しました。次回の企画生成に反映されます。
        </div>
      )}
    </AppShell>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.info}>
      <span className={styles.infoLabel}>{label}</span>
      <span className={styles.infoValue}>{value}</span>
    </div>
  );
}

function Mini({ n, label }: { n: number; label: string }) {
  return (
    <div className={styles.mini}>
      <span className={styles.miniNum}>{n}</span>
      <span className={styles.miniLabel}>{label}</span>
    </div>
  );
}
