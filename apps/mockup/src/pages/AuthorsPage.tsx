import AppShell from "../components/AppShell";
import SectionHeading from "../components/SectionHeading";
import AuthorChip from "../components/AuthorChip";
import { personas, getBooksByAuthor } from "../data";
import { useFavorites, toggleFavorite } from "../data/favoritesStore";
import styles from "./AuthorsPage.module.css";

export default function AuthorsPage() {
  const favorites = useFavorites();

  // 上段: 書店/書庫に本を持つ作家
  const inStore = personas.filter((p) => getBooksByAuthor(p.personaId).length > 0);
  // 下段: お気に入り登録した作家のみ
  const favAuthors = personas.filter((p) => favorites.has(p.personaId));

  return (
    <AppShell topBar={<span className={styles.crumb}>· 作家たち</span>}>
      <SectionHeading
        eyebrow="Authors in your store"
        title="あなたの書店に並んでいる作家たち"
        caption="Publishr が企画ごとに生み出した著者たち。読書ページや著者ページからお気に入りに登録できます。"
      />
      <div className={styles.grid}>
        {inStore.map((p) => (
          <AuthorChip
            key={p.personaId}
            persona={p}
            variant="compact"
            isFavorite={favorites.has(p.personaId)}
            onToggleFav={() => toggleFavorite(p.personaId)}
          />
        ))}
      </div>

      <div className={styles.favSection}>
        <SectionHeading
          eyebrow="Your favorite authors"
          title="あなたのお気に入りの作家"
          caption="お気に入りに登録すると、その著者がこれからもあなたのために本を書き続けます。"
        />
        {favAuthors.length > 0 ? (
          <div className={styles.grid}>
            {favAuthors.map((p) => (
              <AuthorChip
                key={p.personaId}
                persona={p}
                variant="compact"
                isFavorite
                onToggleFav={() => toggleFavorite(p.personaId)}
              />
            ))}
          </div>
        ) : (
          <p className={styles.empty}>
            まだお気に入りの作家はいません。気に入った著者を ☆
            で登録してみてください。
          </p>
        )}
      </div>
    </AppShell>
  );
}
