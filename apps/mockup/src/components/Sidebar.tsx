import { NavLink, useNavigate } from "react-router-dom";
import { getRecentBooks, user, personaById } from "../data";
import BookCover from "./BookCover";
import Logo from "./Logo";
import styles from "./Sidebar.module.css";

const NAV = [
  { to: "/", label: "あなたの書店", icon: "▣" },
  { to: "/library", label: "わたしの書庫", icon: "▤" },
  { to: "/highlights", label: "ハイライト・付箋", icon: "❏" },
  { to: "/authors", label: "作家たち", icon: "✒" },
  { to: "/map", label: "サイトマップ", icon: "✦" },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const recent = getRecentBooks();

  return (
    <aside className={styles.sidebar}>
      <NavLink to="/" className={styles.brand}>
        <span className={styles.logoRow}>
          <Logo size={26} />
          <span className={styles.logo}>Publishr</span>
        </span>
        <span className={styles.tagline}>
          百万部のベストセラーより、
          <br />
          あなたのための一冊。
        </span>
      </NavLink>

      <nav className={styles.nav}>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === "/"}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.active : ""}`
            }
          >
            <span className={styles.navIcon}>{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
      </nav>

      <div className={styles.recent}>
        <span className={styles.recentLabel}>直近の本</span>
        <ul className={styles.recentList}>
          {recent.map((b) => {
            const author = personaById(b.authorPersonaId);
            return (
              <li
                key={b.bookId}
                className={styles.recentItem}
                onClick={() => navigate(`/book/${b.bookId}`)}
              >
                <BookCover family={b.coverFamily} title={b.title} size="spine" />
                <div className={styles.recentMeta}>
                  <span className={styles.recentTitle}>{b.title}</span>
                  <span className={styles.recentAuthor}>{author?.name}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <NavLink
        to="/account"
        className={({ isActive }) =>
          `${styles.user} ${isActive ? styles.userActive : ""}`
        }
      >
        <span className={styles.avatar}>{user.avatarChar}</span>
        <div className={styles.userMeta}>
          <span className={styles.userName}>{user.displayName}</span>
          <span className={styles.userSub}>アカウント設定</span>
        </div>
      </NavLink>
    </aside>
  );
}
