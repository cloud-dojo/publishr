"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { Granularity, ReadingAnnotation } from "@publishr/shared-schema";

import { Topbar } from "@/components/shell/Topbar";
import { applyGranularity, parseBook, splitChapter } from "@/data/bookText";
import { useActions, useProvider } from "@/data/hooks";

const GOOD_REASONS = ["参考になった", "共感した", "実践したい", "もっと知りたい"];
const BAD_REASONS = ["一般論すぎる", "自分には合わない", "内容が難しい", "文体が読みづらい"];
const GRANULARITY_LABELS: Record<Granularity, string> = {
  full: "フル",
  summary: "要約",
  excerpt: "ここだけ",
};
const SEGMENTS: Granularity[] = ["full", "summary"];
const FONT_STEPS = [
  { label: "小", scale: 0.88 },
  { label: "中", scale: 1 },
  { label: "大", scale: 1.2 },
];
const PAGE_GAP = 72;
const BASE_FONT = 16;
const SPREAD_MIN = 640; // クリップ幅がこれ以上なら二面見開き

export default function ReaderPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { sendFeedback, updateReadingState } = useActions();
  const book = provider.getBook(params.bookId);

  const [view, setView] = useState(0);
  const [spreads, setSpreads] = useState(1);
  const [totalCols, setTotalCols] = useState(1);
  const [colsPerView, setColsPerView] = useState(1);
  const [stride, setStride] = useState(1);
  const [turning, setTurning] = useState(false);
  const [selectedPara, setSelectedPara] = useState<number | null>(null);
  const [reaction, setReaction] = useState<"good" | "bad" | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [fontStep, setFontStep] = useState(1);
  const [chapterMarks, setChapterMarks] = useState<{ col: number; label: string }[]>([]);
  const [draftAnnotations, setDraftAnnotations] = useState<ReadingAnnotation[] | null>(null);

  const viewportRef = useRef<HTMLDivElement>(null);
  const clipRef = useRef<HTMLDivElement>(null);
  const flowRef = useRef<HTMLDivElement>(null);
  const spreadsRef = useRef(1);
  const navigatedRef = useRef(false);

  const recompute = useCallback(() => {
    const clip = clipRef.current;
    const flow = flowRef.current;
    if (!clip || !flow) return;
    const cw = clip.clientWidth;
    const n = cw >= SPREAD_MIN ? 2 : 1;
    const colW = Math.max(1, Math.floor((cw - (n - 1) * PAGE_GAP) / n));
    flow.style.columnWidth = `${colW}px`;
    flow.style.columnGap = `${PAGE_GAP}px`;
    const colPitch = colW + PAGE_GAP;
    const cols = Math.max(1, Math.round((flow.scrollWidth + PAGE_GAP) / colPitch));
    const sp = Math.max(1, Math.ceil(cols / n));
    setColsPerView(n);
    setTotalCols(cols);
    setSpreads(sp);
    spreadsRef.current = sp;
    setStride(n * colPitch);
    setView((v) => Math.min(v, sp - 1));
    const openers = Array.from(flow.querySelectorAll<HTMLElement>(".rd-opener"));
    setChapterMarks(
      openers.map((el) => ({ col: Math.round(el.offsetLeft / colPitch), label: el.dataset.ch ?? "" }))
    );
  }, []);

  // 内容・フォント・章精度の変化で再ページ分割
  useLayoutEffect(() => {
    recompute();
  }, [recompute, params.bookId, book?.body, book?.granularity, fontStep]);

  // リサイズ追従
  useEffect(() => {
    const vp = viewportRef.current;
    if (!vp || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => recompute());
    ro.observe(vp);
    return () => ro.disconnect();
  }, [recompute, params.bookId]);

  const go = useCallback((dir: number) => {
    navigatedRef.current = true;
    setView((v) => Math.min(spreadsRef.current - 1, Math.max(0, v + dir)));
    setTurning(true);
    window.setTimeout(() => setTurning(false), 170);
  }, []);

  // キーボード ←/→
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  // 進捗の保存（めくった後のみ）
  useEffect(() => {
    if (!book || !navigatedRef.current) return;
    const pct = Math.round((Math.min((view + 1) * colsPerView, totalCols) / totalCols) * 100);
    if (pct > (book.feedback.readPercent ?? 0)) {
      void sendFeedback(book.id, { readPercent: pct });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, totalCols, colsPerView]);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/library", label: "‹ 書庫" }} notify={false} icon="Aa" />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const annotations = draftAnnotations ?? book.annotations ?? [];
  const allBlocks = parseBook(book.body, book.prefaceSample);
  const blocks = applyGranularity(allBlocks, book.granularity);

  const leftCol = view * colsPerView;
  const leftPage = leftCol + 1;
  const rightPage = Math.min(totalCols, leftCol + colsPerView);
  const pageLabel = rightPage > leftPage ? `${leftPage}–${rightPage}` : `${leftPage}`;
  const progressPct = Math.round((rightPage / totalCols) * 100);
  const currentChapter =
    [...chapterMarks].reverse().find((m) => m.col <= leftCol)?.label || book.subtitle || "";

  const hasMark = (kind: ReadingAnnotation["kind"], pi: number) =>
    annotations.some((a) => a.kind === kind && a.paragraphIndex === pi);
  const paraText = (pi: number) => {
    const b = allBlocks.find((x) => x.kind === "para" && x.pi === pi);
    return b && b.kind === "para" ? b.text : "";
  };

  const persist = (next: ReadingAnnotation[]) => {
    setDraftAnnotations(next);
    void updateReadingState(book.id, { granularity: book.granularity, annotations: next });
  };
  const toggleHighlight = (pi: number, text: string) => {
    setSelectedPara(pi);
    const next = hasMark("highlight", pi)
      ? annotations.filter((a) => !(a.kind === "highlight" && a.paragraphIndex === pi))
      : [
          ...annotations,
          { id: `ann_${book.id}_h${pi}`, kind: "highlight", paragraphIndex: pi, text: text.slice(0, 48), note: null } as ReadingAnnotation,
        ];
    persist(next);
  };
  const addMark = (kind: ReadingAnnotation["kind"]) => {
    const pi = selectedPara ?? 0;
    if (hasMark(kind, pi)) {
      persist(annotations.filter((a) => !(a.kind === kind && a.paragraphIndex === pi)));
      return;
    }
    persist([
      ...annotations,
      {
        id: `ann_${book.id}_${kind}${pi}`,
        kind,
        paragraphIndex: pi,
        text: paraText(pi).slice(0, 48),
        note: kind === "note" ? "ここ、次に活かす。" : kind === "bookmark" ? "あとで読み返す" : null,
      },
    ]);
  };
  const setReactionFB = (value: string | null) => {
    void sendFeedback(book.id, { readingReaction: value });
  };
  const chooseReaction = (value: "good" | "bad") => {
    if (reaction === value) {
      setReaction(null);
      setReason(null);
      setReactionFB(null);
    } else {
      setReaction(value);
      setReason(null);
      setReactionFB(value);
    }
  };
  const pickReason = (r: string) => {
    if (reason === r) {
      setReason(null);
      if (reaction) setReactionFB(reaction);
    } else {
      setReason(r);
      if (reaction) setReactionFB(`${reaction}:${r}`);
    }
  };

  return (
    <>
      <header className="topbar">
        <div className="reader-top">
          <Link href="/library" className="greeting">
            ‹ 書庫
          </Link>
          <div className="rt-title">
            {book.title} <span>／ {persona?.name}</span>
          </div>
        </div>
        <div style={{ marginLeft: "auto" }} className="row gap12">
          <div className="segment">
            {SEGMENTS.map((g) => (
              <button
                key={g}
                className={book.granularity === g ? "on" : ""}
                onClick={() => updateReadingState(book.id, { granularity: g, annotations })}
              >
                {GRANULARITY_LABELS[g]}
              </button>
            ))}
          </div>
          <div className="segment aa-segment" title="文字サイズ">
            <span className="aa-mark">Aa</span>
            {FONT_STEPS.map((f, i) => (
              <button
                key={f.label}
                type="button"
                className={i === fontStep ? "on" : ""}
                onClick={() => setFontStep(i)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="reading">
        <div className="rd-stage">
          <button
            type="button"
            className="rd-nav rd-nav--prev"
            onClick={() => go(-1)}
            disabled={view === 0}
            aria-label="前のページ"
          >
            ‹
          </button>

          <div
            className={`reader-viewport reveal${colsPerView > 1 ? " spread" : ""}`}
            ref={viewportRef}
          >
            <div className="rd-runhead">
              <span className="rh-book">{book.title}</span>
              <span className="rh-chap">{currentChapter}</span>
            </div>

            <div className="page-clip" ref={clipRef}>
              <div
                className={`page-flow${turning ? " is-turning" : ""}`}
                ref={flowRef}
                style={{
                  transform: `translateX(-${view * stride}px)`,
                  fontSize: `${BASE_FONT * FONT_STEPS[fontStep].scale}px`,
                }}
              >
                {blocks.map((b, i) => {
                  if (b.kind === "chapter") {
                    const { no, title } = splitChapter(b.text);
                    return (
                      <section key={`c${i}`} className="rd-opener" data-ch={b.text}>
                        {no && <div className="rd-opener-no">{no}</div>}
                        <div className="rd-opener-rule" />
                        <h2 className="rd-opener-title">{title || b.text}</h2>
                      </section>
                    );
                  }
                  return (
                    <p
                      key={`p${b.pi}`}
                      data-pi={b.pi}
                      className={`${b.lead ? "lead " : ""}${selectedPara === b.pi ? "sel" : ""}`}
                      onClick={() => toggleHighlight(b.pi, b.text)}
                    >
                      {hasMark("highlight", b.pi) ? (
                        <mark className={`hl${hasMark("note", b.pi) ? " note" : ""}`}>{b.text}</mark>
                      ) : (
                        b.text
                      )}
                    </p>
                  );
                })}
              </div>
            </div>

            <div className="rd-runfoot">
              <span>
                {pageLabel} <i>/ {totalCols} ページ</i>
              </span>
              <span className="rf-prog">
                <span className="rf-bar">
                  <i style={{ width: `${progressPct}%` }} />
                </span>
                {progressPct}%
              </span>
            </div>
          </div>

          <button
            type="button"
            className="rd-nav rd-nav--next"
            onClick={() => go(1)}
            disabled={view >= spreads - 1}
            aria-label="次のページ"
          >
            ›
          </button>
        </div>

        <aside className="rail-tools">
          <div className="tool-card panel">
            <div className="tc-h">
              <span className="k">✎</span> このページの操作
            </div>
            <div className="tool-actions">
              <button
                className={`icon-btn${selectedPara !== null && hasMark("highlight", selectedPara) ? " on" : ""}`}
                type="button"
                title="選択中の段落をハイライト"
                onClick={() => selectedPara !== null && toggleHighlight(selectedPara, paraText(selectedPara))}
              >
                🖊
              </button>
              <button className="icon-btn" type="button" title="付箋" onClick={() => addMark("note")}>
                🏷
              </button>
              <button className="icon-btn" type="button" title="栞" onClick={() => addMark("bookmark")}>
                🔖
              </button>
            </div>
            <div className="muted" style={{ fontSize: 11.5, marginTop: 10, lineHeight: 1.5 }}>
              本文の段落をクリックすると、その段落にハイライトを引けます（もう一度で解除）。付箋・栞は選択中の段落に付きます。
            </div>
          </div>

          <div className="tool-card panel">
            <div className="tc-h">
              <span className="k">◇</span> この本へのフィードバック
            </div>
            <div className="fb-q">この本は、あなたに響きましたか？</div>
            <div className="gb-row">
              <button
                type="button"
                className={`gb-btn${reaction === "good" ? " on good" : ""}`}
                onClick={() => chooseReaction("good")}
              >
                👍 いいね
              </button>
              <button
                type="button"
                className={`gb-btn${reaction === "bad" ? " on bad" : ""}`}
                onClick={() => chooseReaction("bad")}
              >
                👎 いまいち
              </button>
            </div>

            {reaction && (
              <div className="gb-reasons">
                <div className="gb-reasons-q">
                  {reaction === "good" ? "どこが良かったですか？" : "どこが気になりましたか？"}
                </div>
                <div className="fb-opts">
                  {(reaction === "good" ? GOOD_REASONS : BAD_REASONS).map((r) => (
                    <div
                      key={r}
                      className={`chip${reason === r ? " on" : ""}`}
                      onClick={() => pickReason(r)}
                    >
                      {r}
                    </div>
                  ))}
                  <div
                    className={`chip${reason === "その他" ? " on" : ""}`}
                    onClick={() => pickReason("その他")}
                  >
                    その他
                  </div>
                </div>
                {reason === "その他" && (
                  <div className="gb-other-note">
                    詳しい感想は、下の「読み終えた → 感想を書く」からご記入ください。
                  </div>
                )}
              </div>
            )}

            <div className="muted" style={{ fontSize: 11, marginTop: 10, lineHeight: 1.5 }}>
              あなたの選択は次の入荷の企画に反映されます。
            </div>
          </div>

          <Link href={`/read/${book.id}/finish`} className="btn btn--gold btn--block">
            読み終えた → 感想を書く
          </Link>
        </aside>
      </div>
    </>
  );
}
