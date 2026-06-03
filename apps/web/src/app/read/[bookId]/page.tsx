"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type { Granularity, ReadingAnnotation } from "@publishr/shared-schema";

import { Topbar } from "@/components/shell/Topbar";
import { useActions, useProvider } from "@/data/hooks";

const FB_OPTIONS = ["▲ まさに今ほしかった", "○ 参考になった", "△ 少し一般的すぎる", "▽ 自分には早い"];
const GRANULARITY_LABELS: Record<Granularity, string> = {
  full: "フル",
  summary: "要約",
  excerpt: "ここだけ",
};

function parseBody(body: string): { chapter: string; paras: string[] } {
  const paras: string[] = [];
  let chapter = "";
  let buf: string[] = [];
  const flush = () => {
    if (buf.length) {
      paras.push(buf.join(""));
      buf = [];
    }
  };
  for (const line of body.split("\n")) {
    if (line.startsWith("## ")) {
      flush();
      chapter = line.slice(3).trim();
      continue;
    }
    if (line.trim() === "") {
      flush();
      continue;
    }
    buf.push(line.trim());
  }
  flush();
  return { chapter, paras };
}

export default function ReaderPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const { updateReadingState } = useActions();
  const [fb, setFb] = useState<number | null>(null);
  const [draftAnnotations, setDraftAnnotations] = useState<ReadingAnnotation[] | null>(null);
  const book = provider.getBook(params.bookId);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: "/", label: "‹ 書庫" }} notify={false} icon="Aa" />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const content = book.body
    ? parseBody(book.body)
    : { chapter: book.subtitle || book.title, paras: book.prefaceSample.split("\n\n").filter(Boolean) };
  const annotations = draftAnnotations ?? book.annotations ?? [];
  const visibleParas =
    book.granularity === "excerpt"
      ? content.paras.slice(0, 1).map((p) => (p.includes("。") ? `${p.split("。")[0]}。` : p))
      : book.granularity === "summary"
        ? content.paras.slice(0, 1)
        : content.paras;
  const saveReadingState = (next: { granularity?: Granularity; annotations?: ReadingAnnotation[] }) => {
    void updateReadingState(book.id, {
      granularity: next.granularity ?? book.granularity,
      annotations: next.annotations ?? annotations,
    });
  };
  const addAnnotation = (kind: ReadingAnnotation["kind"]) => {
    const text = visibleParas[0] ?? content.chapter;
    const nextAnnotations = annotations.filter((a) => !(a.kind === kind && a.paragraphIndex === 0));
    const next: ReadingAnnotation = {
      id: `ann_${book.id}_${nextAnnotations.length + 1}_${kind}`,
      kind,
      paragraphIndex: 0,
      text: text.slice(0, 40),
      note:
        kind === "note"
          ? "ここ、次の1on1で使う。"
          : kind === "bookmark"
            ? "あとで読み返す"
            : null,
    };
    const merged = [...nextAnnotations, next];
    setDraftAnnotations(merged);
    saveReadingState({ annotations: merged });
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
            {(Object.keys(GRANULARITY_LABELS) as Granularity[]).map((g) => (
              <button
                key={g}
                className={book.granularity === g ? "on" : ""}
                onClick={() => saveReadingState({ granularity: g })}
              >
                {GRANULARITY_LABELS[g]}
              </button>
            ))}
          </div>
          <div className="icon-btn">Aa</div>
        </div>
      </header>

      <div className="reading">
        <article className="paper-page reveal">
          <div className="chap-no">{book.subtitle || "本文"}</div>
          <div className="chap-title">{content.chapter}</div>
          {visibleParas.map((p, i) => {
            const paragraphAnnotations = annotations.filter((a) => a.paragraphIndex === i);
            const highlighted = paragraphAnnotations.some((a) => a.kind === "highlight");
            return (
            <div key={i}>
              <p className={i === 0 ? "lead" : ""}>{highlighted ? <mark className="hl">{p}</mark> : p}</p>
              {paragraphAnnotations
                .filter((a) => a.kind === "note")
                .map((a) => (
                  <div key={a.id} className="sticky">
                    {a.note ?? a.text}
                  </div>
                ))}
              {paragraphAnnotations.some((a) => a.kind === "bookmark") && (
                <div className="sticky">🔖 あとで読み返す</div>
              )}
            </div>
            );
          })}
        </article>

        <aside className="rail-tools">
          <div className="tool-card panel">
            <div className="tc-h">
              <span className="k">✎</span> このページの操作
            </div>
            <div className="tool-actions">
              <button className="icon-btn" type="button" onClick={() => addAnnotation("highlight")}>🖊</button>
              <button className="icon-btn" type="button" onClick={() => addAnnotation("note")}>🏷</button>
              <button className="icon-btn" type="button" onClick={() => addAnnotation("bookmark")}>🔖</button>
            </div>
            <div className="muted" style={{ fontSize: 11.5, marginTop: 10, lineHeight: 1.5 }}>
              デモでは先頭段落にハイライト・付箋・栞を付けられます。
            </div>
          </div>

          <div className="tool-card panel">
            <div className="tc-h">
              <span className="k">◇</span> 読みながら、ひとこと
            </div>
            <div className="fb-q">この章は、いまのあなたに役立ちそうですか？</div>
            <div className="fb-opts">
              {FB_OPTIONS.map((label, i) => (
                <div
                  key={i}
                  className={`chip ${fb === i ? "on" : ""}`}
                  onClick={() => setFb(i)}
                >
                  {label}
                </div>
              ))}
            </div>
            <div className="muted" style={{ fontSize: 11, marginTop: 10, lineHeight: 1.5 }}>
              あなたの選択は次の入荷の企画に反映されます。
            </div>
          </div>

          <Link href={`/read/${book.id}/finish`} className="btn btn--gold btn--block">
            読み終えた → 感想を書く
          </Link>
        </aside>
      </div>

      <div className="progress-foot">
        <span className="ptext">本文 / 全{book.estimatedChapters}章</span>
        <div className="pbar">
          <i style={{ width: "62%" }} />
        </div>
        <span className="ptext">62% ・ 残り約{Math.round(book.estimatedMinutes * 0.38)}分</span>
      </div>
    </>
  );
}
