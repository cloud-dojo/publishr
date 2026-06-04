import { useNavigate } from "react-router-dom";
import type { Book, Plan } from "../data/types";
import { personaById } from "../data";
import BookCover from "./BookCover";
import StatusBadge from "./StatusBadge";
import ThemeBadge from "./ThemeBadge";
import Stars from "./Stars";
import styles from "./BookCard.module.css";

interface Props {
  book: Book;
  plan?: Plan; // 入荷理由を表示する場合（書店トップ draft）
  showReason?: boolean;
  showStatus?: boolean; // ステータスバッジ（入荷/予約中/既読）。既定true
  showThemeBadge?: boolean; // 種別タグ（関心/新しい出会い）。既定false
  onClick?: () => void;
}

export default function BookCard({
  book,
  plan,
  showReason,
  showStatus = true,
  showThemeBadge = false,
  onClick,
}: Props) {
  const navigate = useNavigate();
  const author = personaById(book.authorPersonaId);
  const go = onClick ?? (() => navigate(`/book/${book.bookId}`));

  return (
    <article className={styles.card} onClick={go}>
      <BookCover family={book.coverFamily} title={book.title} size="md" />
      <div className={styles.body}>
        {(showStatus || showThemeBadge) && (
          <div className={styles.badges}>
            {showThemeBadge && <ThemeBadge kind={book.themeKind} />}
            {showStatus && <StatusBadge status={book.status} />}
          </div>
        )}
        <h3 className={styles.title}>{book.title}</h3>
        <span className={styles.author}>{author?.name}</span>

        {book.feedback?.rating != null && (
          <Stars value={book.feedback.rating} />
        )}

        {showReason && plan && (
          <p className={styles.reason}>
            <span className={styles.reasonLabel}>入荷理由</span>
            {plan.reason}
          </p>
        )}
      </div>
    </article>
  );
}
