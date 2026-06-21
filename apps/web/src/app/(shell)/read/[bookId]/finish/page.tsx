"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { StarRating } from "@/components/postread/StarRating";
import { Topbar } from "@/components/shell/Topbar";
import { useActions, useProvider } from "@/data/hooks";

export default function FinishPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { sendFeedback, notifyFavoriteAuthor } = useActions();
  const book = provider.getBook(params.bookId);

  const [rating, setRating] = useState<number | null>(book?.feedback.rating ?? null);
  const [following, setFollowing] = useState(false);
  const [impression, setImpression] = useState(book?.feedback.impression ?? "");
  const [saved, setSaved] = useState(false);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);

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
      <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} />
      <div className="page-hero">
        <div className="ph-eyebrow">You finished a book</div>
        <h1>
          読了、おつかれさまでした。<br />
          この一冊は<span className="accent">いかがでしたか？</span>
        </h1>
      </div>

      <div className="postread">
        <div className="panel">
          <div style={{ fontFamily: "var(--font-display)", fontSize: 20, color: "var(--text-100)", marginBottom: 18 }}>
            『{book.title}』 ／ {persona?.name}
          </div>
          <StarRating value={rating} onChange={onRate} />
          <div className="muted" style={{ fontSize: 12.5, marginTop: 12 }}>
            {rating ? `★${rating} を記録しました。次の入荷に反映されます。` : "星をタップして評価してください。"}
          </div>

          <div className="pr-actions">
            <button
              type="button"
              className={following ? "btn btn--gold" : "btn btn--ghost"}
              onClick={() => {
                const next = !following;
                if (next && persona) notifyFavoriteAuthor(persona.id, persona.name, book.id);
                setFollowing(next);
              }}
            >
              {following ? "♥ お気に入りの作家に登録済み" : `♡ ${persona?.name} をお気に入りに`}
            </button>
          </div>
        </div>

        <div className="panel">
          <div style={{ fontFamily: "var(--font-display)", fontSize: 16, color: "var(--text-100)", marginBottom: 6 }}>
            この本の感想
          </div>
          <div className="muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
            心に残った一節や、明日から試したいこと。自由に書き残せます。
          </div>
          <textarea
            className="impression-input"
            rows={5}
            placeholder="例：『任せる』と『放る』は違う、という一文が刺さった。来週の1on1で、権限の線引きを見直してみる。"
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
              <span className="muted" style={{ fontSize: 12.5 }}>
                保存しました。あなたの言葉は次の入荷の参考になります。
              </span>
            )}
          </div>
        </div>

        {following && persona && (
          <div className="sequel">
            <div style={{ fontSize: 26 }}>✦</div>
            <div style={{ flex: 1 }}>
              <div className="sq-t">お気に入りの作家が、次の一冊を考えはじめました</div>
              <div className="sq-d">
                あなたがお気に入り登録した {persona.name} は、次回作を検討しています。新しい一冊が入荷した際はご案内します。
              </div>
            </div>
          </div>
        )}

        <div className="row gap12" style={{ justifyContent: "center", marginTop: 28 }}>
          <Link href="/" className="btn btn--ghost">
            書店にもどる
          </Link>
        </div>
      </div>
    </>
  );
}
