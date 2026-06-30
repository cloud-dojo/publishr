"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { StarRating } from "@/components/postread/StarRating";
import { BackLink } from "@/components/shell/NavigationHistory";
import { Topbar } from "@/components/shell/Topbar";
import { toggleFavorite, useFavorites } from "@/data/favorites-store";
import { useActions, useProvider } from "@/data/hooks";

export default function FinishPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { sendFeedback, notifyFavoriteAuthor } = useActions();
  // お気に入りは /authors と同じ正本ストア（localStorage＋Firestore favoriteAuthors）を読む。
  const favorites = useFavorites();
  const book = provider.getBook(params.bookId);

  const [rating, setRating] = useState<number | null>(book?.feedback.rating ?? null);
  const [impression, setImpression] = useState(book?.feedback.impression ?? "");
  const [saved, setSaved] = useState(false);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ 書店へ戻る" }} />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const isFav = persona ? favorites.has(persona.id) : false;

  const onRate = (n: number) => {
    setRating(n);
    void sendFeedback(book.id, { rating: n, readPercent: 100 });
  };
  const onSaveImpression = () => {
    const text = impression.trim();
    if (!text) return;
    // 自由記述感想を Firestore に保存（feedback.impression・サーバ側で制御文字除去＋長さ制限）。
    void sendFeedback(book.id, { impression: text });
    setSaved(true);
  };

  return (
    <>
      <Topbar back={{ href: "/", label: "‹ 書店へ戻る" }} />
      <div className="scaled-page finish-page">
      <div className="page-hero">
        <div className="ph-eyebrow">You finished a book</div>
        <h1>
          読了、おつかれさまでした。<br />
          この一冊は<span className="accent">いかがでしたか？</span>
        </h1>
      </div>

      <div className="postread">
        <div className="panel">
          <div className="postread-book-title">
            『{book.title}』 ／ {persona?.name}
          </div>
          <StarRating value={rating} onChange={onRate} />
          <div className="muted postread-help">
            {rating ? `★${rating} を記録しました。次に届く本に反映されます。` : "星をタップして評価してください。"}
          </div>

          <div className="pr-actions">
            <button
              type="button"
              className={isFav ? "btn btn--gold" : "btn btn--ghost"}
              onClick={() => {
                if (!persona) return;
                const wasFav = favorites.has(persona.id);
                // 正本ストアへ登録/解除（/authors の★と一致・Firestore favoriteAuthors にも反映）。
                toggleFavorite({
                  personaId: persona.id,
                  name: persona.name,
                  voiceStyle: persona.voiceStyle ?? "",
                  format: persona.format ?? "",
                  savedAt: new Date().toISOString(),
                });
                // 新規登録時のみ通知を出す（解除時は出さない）。
                if (!wasFav) notifyFavoriteAuthor(persona.id, persona.name, book.id);
              }}
            >
              {isFav ? "♥ お気に入りの作家に登録済み" : `♡ ${persona?.name} をお気に入りに`}
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="postread-panel-title">
            この本の感想
          </div>
          <div className="muted postread-lead">
            心に残った一節や、明日から試したいこと。自由に書き残せます。
          </div>
          <textarea
            className="impression-input"
            rows={5}
            placeholder="例：『任せる』と『放る』は違う、という一文が刺さった。次の1on1で、権限の線引きを見直してみる。"
            value={impression}
            onChange={(e) => {
              setImpression(e.target.value);
              setSaved(false);
            }}
          />
          <div className="row gap12" style={{ marginTop: 12, alignItems: "center" }}>
            <button
              type="button"
              className="btn btn--gold"
              onClick={onSaveImpression}
              disabled={!impression.trim()}
            >
              感想を保存
            </button>
            {saved && (
              <span className="muted postread-help">
                保存しました。あなたの言葉は次に届く本の参考になります。
              </span>
            )}
          </div>
        </div>

        {isFav && persona && (
          <div className="sequel">
            <div className="sequel-icon">✦</div>
            <div style={{ flex: 1 }}>
              <div className="sq-t">お気に入りの作家が、次の一冊を考えはじめました</div>
              <div className="sq-d">
                あなたがお気に入り登録した {persona.name} は、次回作を検討しています。新しい一冊が届いたらご案内します。
              </div>
            </div>
          </div>
        )}

        <div className="row gap12" style={{ justifyContent: "center", marginTop: 28 }}>
          <BackLink href="/" className="btn btn--ghost">
            書店へ戻る
          </BackLink>
        </div>
      </div>
      </div>
    </>
  );
}
