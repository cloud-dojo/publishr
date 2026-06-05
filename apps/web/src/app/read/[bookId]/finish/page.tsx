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
  const { sendFeedback } = useActions();
  const book = provider.getBook(params.bookId);

  const [rating, setRating] = useState<number | null>(book?.feedback.rating ?? null);
  const [following, setFollowing] = useState(false);
  const [wantsSequel, setWantsSequel] = useState(book?.feedback.wantsSequel ?? false);
  const [impression, setImpression] = useState("");
  const [saved, setSaved] = useState(false);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} notify={false} icon="♡" />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);

  const onRate = (n: number) => {
    setRating(n);
    void sendFeedback(book.id, { rating: n, readPercent: 100 });
  };
  const onSequel = () => {
    const next = !wantsSequel;
    setWantsSequel(next);
    void sendFeedback(book.id, { wantsSequel: next });
  };
  const onSaveImpression = () => {
    // mock: 自由記入の感想をローカル保存（フェーズ3で Firestore 直書きに差し替え）。
    if (typeof window !== "undefined") {
      window.localStorage.setItem(`publishr.impression.${book.id}`, impression);
    }
    setSaved(true);
  };

  return (
    <>
      <Topbar back={{ href: "/", label: "‹ あなたの書店にもどる" }} notify={false} icon="♡" />
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
              onClick={() => setFollowing((v) => !v)}
            >
              {following ? "♥ お気に入りの作家に登録済み" : `♡ ${persona?.name} をお気に入りに`}
            </button>
            <button
              type="button"
              className={wantsSequel ? "btn btn--gold" : "btn btn--ghost"}
              onClick={onSequel}
            >
              {wantsSequel ? "✦ 続編を希望中" : "続編を希望する"}
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

        {(following || wantsSequel) && persona && (
          <div className="sequel">
            <div style={{ fontSize: 26 }}>✦</div>
            <div style={{ flex: 1 }}>
              <div className="sq-t">あなたの反応を受けて、{persona.name} が次の一冊を構想中です</div>
              <div className="sq-d">
                あなたの高評価と続編希望から、関連テーマの新刊を明朝の入荷候補に加えました。
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
