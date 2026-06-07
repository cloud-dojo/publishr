"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import type { Granularity, HighlightColor, ReadingAnnotation } from "@publishr/shared-schema";

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
const SPREAD_MIN = 640;

const HL_COLORS: { value: HighlightColor; label: string }[] = [
  { value: "yellow", label: "黄" },
  { value: "blue",   label: "青" },
  { value: "pink",   label: "桃" },
];

// 段落内のハイライトをレンジ別に描画するヘルパー
function renderParaContent(
  text: string,
  highlights: ReadingAnnotation[],
  onMarkClick: (e: React.MouseEvent<HTMLElement>, annId: string) => void
): React.ReactNode {
  if (highlights.length === 0) return text;

  // startOffset が未設定（旧形式）= 段落全体ハイライト
  const legacy = highlights.find((a) => typeof a.startOffset !== "number");
  if (legacy) {
    return (
      <mark
        className={`hl hl-${legacy.color ?? "yellow"}`}
        data-ann-id={legacy.id}
        onClick={(e) => { e.stopPropagation(); onMarkClick(e, legacy.id); }}
      >
        {text}
      </mark>
    );
  }

  // ranged highlights: 重複を除外し startOffset 順にソート
  const sorted = [...highlights]
    .filter((a) => typeof a.startOffset === "number")
    .sort((a, b) => (a.startOffset ?? 0) - (b.startOffset ?? 0));

  const segments: React.ReactNode[] = [];
  let pos = 0;
  for (const ann of sorted) {
    const start = Math.max(pos, ann.startOffset ?? 0);
    const end = Math.min(ann.endOffset ?? text.length, text.length);
    if (start >= end) continue;
    if (pos < start) segments.push(text.slice(pos, start));
    segments.push(
      <mark
        key={ann.id}
        className={`hl hl-${ann.color ?? "yellow"}`}
        data-ann-id={ann.id}
        onClick={(e) => { e.stopPropagation(); onMarkClick(e, ann.id); }}
      >
        {text.slice(start, end)}
      </mark>
    );
    pos = end;
  }
  if (pos < text.length) segments.push(text.slice(pos));
  return <>{segments}</>;
}

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
  const [reaction, setReaction] = useState<"good" | "bad" | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [fontStep, setFontStep] = useState(1);
  const [chapterMarks, setChapterMarks] = useState<{ col: number; label: string }[]>([]);
  const [draftAnnotations, setDraftAnnotations] = useState<ReadingAnnotation[] | null>(null);
  const [currentPi, setCurrentPi] = useState<number>(-1);

  // ハイライトポップアップ: クリックしたハイライトの annId と表示座標
  const [hlPopup, setHlPopup] = useState<{ annId: string; x: number; y: number } | null>(null);

  const viewportRef = useRef<HTMLDivElement>(null);
  const clipRef = useRef<HTMLDivElement>(null);
  const flowRef = useRef<HTMLDivElement>(null);
  const spreadsRef = useRef(1);
  const strideRef = useRef(1);
  const navigatedRef = useRef(false);
  const jumpedRef = useRef(false);
  const lastViewRef = useRef(0);

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
    strideRef.current = n * colPitch;
    setView((v) => Math.min(v, sp - 1));
    const openers = Array.from(flow.querySelectorAll<HTMLElement>(".rd-opener"));
    setChapterMarks(
      openers.map((el) => ({ col: Math.round(el.offsetLeft / colPitch), label: el.dataset.ch ?? "" }))
    );
  }, []);

  useLayoutEffect(() => {
    recompute();
    // 目次/ハイライト一覧から ?ch=<章index> / ?pi=<段落index> 付きで来たら、その箇所のページへ一度だけ移動。
    if (jumpedRef.current) return;
    const flow = flowRef.current;
    if (!flow) return;
    const q = new URLSearchParams(window.location.search);
    const piParam = q.get("pi");
    const chParam = q.get("ch");
    let el: HTMLElement | null = null;
    if (piParam != null) {
      el = flow.querySelector<HTMLElement>(`[data-pi="${CSS.escape(piParam)}"]`);
    } else if (chParam != null) {
      el = flow.querySelectorAll<HTMLElement>(".rd-opener")[Number(chParam)] ?? null;
    }
    if (el) {
      const v = Math.max(0, Math.min(spreadsRef.current - 1, Math.floor(el.offsetLeft / strideRef.current)));
      setView(v);
      jumpedRef.current = true;
    } else {
      // ?ch / ?pi なし → 前回離脱位置から再開
      const saved = localStorage.getItem(`read_view_${params.bookId}`);
      if (saved) {
        const v = Math.min(spreadsRef.current - 1, Math.max(0, parseInt(saved, 10)));
        if (v > 0) {
          setView(v);
          jumpedRef.current = true;
        }
      }
    }
  }, [recompute, params.bookId, book?.body, book?.granularity, fontStep]);

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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  useEffect(() => {
    if (!book || !navigatedRef.current) return;
    const pct = Math.round((Math.min((view + 1) * colsPerView, totalCols) / totalCols) * 100);
    if (pct > (book.feedback.readPercent ?? 0)) {
      void sendFeedback(book.id, { readPercent: pct });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, totalCols, colsPerView]);

  // ポップアップ外クリックで閉じる
  useEffect(() => {
    if (!hlPopup) return;
    const handler = (e: MouseEvent) => {
      const popup = document.querySelector(".hl-popup");
      if (popup?.contains(e.target as Node)) return;
      setHlPopup(null);
    };
    window.addEventListener("mousedown", handler);
    return () => window.removeEventListener("mousedown", handler);
  }, [hlPopup]);

  // 現在 view を lastViewRef に記録（アンマウント時に localStorage へ保存するため）
  useEffect(() => {
    lastViewRef.current = view;
  }, [view]);

  // 離脱時に最終スプレッド番号を保存
  useEffect(() => {
    return () => {
      if (lastViewRef.current > 0) {
        localStorage.setItem(`read_view_${params.bookId}`, String(lastViewRef.current));
      }
    };
  }, [params.bookId]);

  // 現在スプレッドの最初の段落インデックスを追跡（ブックマーク用）
  useLayoutEffect(() => {
    const flow = flowRef.current;
    if (!flow || stride === 0) return;
    const leftEdge = view * stride;
    const rightEdge = leftEdge + stride;
    for (const p of Array.from(flow.querySelectorAll<HTMLElement>("p[data-pi]"))) {
      if (p.offsetLeft >= leftEdge && p.offsetLeft < rightEdge) {
        setCurrentPi(parseInt(p.getAttribute("data-pi") ?? "-1", 10));
        return;
      }
    }
    setCurrentPi(-1);
  }, [view, stride]);

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

  // --- annotation helpers ---
  const persist = (next: ReadingAnnotation[]) => {
    setDraftAnnotations(next);
    void updateReadingState(book.id, { granularity: book.granularity, annotations: next });
  };

  const isPageBookmarked = currentPi >= 0 && annotations.some(
    (a) => a.kind === "bookmark" && a.paragraphIndex === currentPi
  );

  const toggleBookmark = () => {
    const flow = flowRef.current;
    if (!flow || stride === 0) return;
    const leftEdge = view * stride;
    const rightEdge = leftEdge + stride;
    let pi = -1;
    for (const p of Array.from(flow.querySelectorAll<HTMLElement>("p[data-pi]"))) {
      if (p.offsetLeft >= leftEdge && p.offsetLeft < rightEdge) {
        pi = parseInt(p.getAttribute("data-pi") ?? "-1", 10);
        break;
      }
    }
    if (pi < 0) return;
    const existing = annotations.find((a) => a.kind === "bookmark" && a.paragraphIndex === pi);
    if (existing) {
      persist(annotations.filter((a) => a.id !== existing.id));
    } else {
      const el = flow.querySelector<HTMLElement>(`p[data-pi="${pi}"]`);
      const text = (el?.textContent ?? "").trim().slice(0, 48);
      persist([...annotations, {
        id: `ann_${book.id}_bk${pi}_${Date.now()}`,
        kind: "bookmark" as const,
        paragraphIndex: pi,
        text,
      }]);
    }
  };

  // 段落のハイライト一覧
  const paraHighlights = (pi: number) =>
    annotations.filter((a) => a.kind === "highlight" && a.paragraphIndex === pi);

  // ドラッグ選択 → ハイライト生成
  const onFlowMouseUp = () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return;

    const range = sel.getRangeAt(0);
    const selectedText = sel.toString().trim();
    if (!selectedText) { sel.removeAllRanges(); return; }

    // 選択開始位置の <p data-pi="..."> を探す
    const findPara = (node: Node): HTMLElement | null => {
      let curr: Node | null = node;
      while (curr) {
        if (curr instanceof HTMLElement && curr.tagName === "P" && curr.getAttribute("data-pi") !== null) {
          return curr;
        }
        curr = curr.parentNode;
      }
      return null;
    };

    const startPara = findPara(range.startContainer);
    if (!startPara) { sel.removeAllRanges(); return; }

    const pi = parseInt(startPara.getAttribute("data-pi") ?? "-1", 10);
    if (pi < 0) { sel.removeAllRanges(); return; }

    // 段落先頭からの文字オフセットを計算
    const preRange = document.createRange();
    preRange.setStart(startPara, 0);
    preRange.setEnd(range.startContainer, range.startOffset);
    const startOffset = preRange.toString().length;
    const endOffset = startOffset + selectedText.length;

    const annId = `ann_${book.id}_h${pi}_${startOffset}_${Date.now()}`;
    const newAnn: ReadingAnnotation = {
      id: annId,
      kind: "highlight",
      paragraphIndex: pi,
      text: selectedText.slice(0, 48),
      note: null,
      color: "yellow",
      startOffset,
      endOffset,
    };

    persist([...annotations, newAnn]);
    sel.removeAllRanges();
  };

  // ハイライト → ポップアップ表示
  const onMarkClick = (e: React.MouseEvent<HTMLElement>, annId: string) => {
    setHlPopup({ annId, x: e.clientX, y: e.clientY });
  };

  // 色変更
  const changeHlColor = (annId: string, color: HighlightColor) => {
    persist(annotations.map((a) => (a.id === annId ? { ...a, color } : a)));
    setHlPopup(null);
  };

  // ハイライト削除
  const deleteHighlight = (annId: string) => {
    persist(annotations.filter((a) => a.id !== annId));
    setHlPopup(null);
  };

  // フィードバック
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

      {/* ハイライト操作ポップアップ */}
      {hlPopup && (
        <div
          className="hl-popup"
          style={{ left: hlPopup.x, top: hlPopup.y }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {HL_COLORS.map(({ value, label }) => (
            <button
              key={value}
              className={`hl-popup-swatch hl-popup-swatch--${value}`}
              title={label}
              onClick={() => changeHlColor(hlPopup.annId, value)}
              aria-label={`色を${label}に変更`}
            />
          ))}
          <div className="hl-popup-sep" />
          <button
            className="hl-popup-delete"
            title="削除"
            onClick={() => deleteHighlight(hlPopup.annId)}
            aria-label="ハイライトを削除"
          >
            ✕
          </button>
        </div>
      )}

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
                onMouseUp={onFlowMouseUp}
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
                  const pHighlights = paraHighlights(b.pi);
                  return (
                    <p
                      key={`p${b.pi}`}
                      data-pi={b.pi}
                      className={b.lead ? "lead" : ""}
                    >
                      {renderParaContent(b.text, pHighlights, onMarkClick)}
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

            <button
              type="button"
              className={`bk-ribbon${isPageBookmarked ? " on" : ""}`}
              onClick={toggleBookmark}
              title={isPageBookmarked ? "ブックマーク解除" : "このページをブックマーク"}
            >
              🔖
            </button>
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
          <nav className="tool-card panel rd-nav-card">
            <Link href={`/read/${book.id}/contents`} className="rd-navrow">
              <span className="rd-navrow-ico">☰</span>
              <span className="rd-navrow-label">目次</span>
              <span className="rd-navrow-arrow">›</span>
            </Link>
            <Link href={`/read/${book.id}/highlights`} className="rd-navrow">
              <span className="rd-navrow-ico">✎</span>
              <span className="rd-navrow-label">ハイライト</span>
              <span className="rd-navrow-arrow">›</span>
            </Link>
            <Link href={`/read/${book.id}/bookmarks`} className="rd-navrow">
              <span className="rd-navrow-ico">⊡</span>
              <span className="rd-navrow-label">ブックマーク</span>
              <span className="rd-navrow-arrow">›</span>
            </Link>
            <Link href={`/books/${book.id}`} className="rd-navrow">
              <span className="rd-navrow-ico">◈</span>
              <span className="rd-navrow-label">本の概要</span>
              <span className="rd-navrow-arrow">›</span>
            </Link>
          </nav>

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

            {/* いいね/いまいちを押したときだけ理由チップを表示（一瞬で出現、アニメーションなし）。
                feedback カードの下方向にのみ伸びるので、上の目次カードは動かない。 */}
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
