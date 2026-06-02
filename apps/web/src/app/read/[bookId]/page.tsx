"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

const FB_OPTIONS = ["▲ まさに今ほしかった", "○ 参考になった", "△ 少し一般的すぎる", "▽ 自分には早い"];

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
  const [fb, setFb] = useState<number | null>(null);
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
            <button>フル</button>
            <button className="on">標準</button>
            <button>要約</button>
            <button>ここだけ</button>
          </div>
          <div className="icon-btn">Aa</div>
        </div>
      </header>

      <div className="reading">
        <article className="paper-page reveal">
          <div className="chap-no">{book.subtitle || "本文"}</div>
          <div className="chap-title">{content.chapter}</div>
          {content.paras.map((p, i) => (
            <div key={i}>
              <p className={i === 0 ? "lead" : ""}>{p}</p>
              {book.id === "b_makasekata" && i === 0 && (
                <div className="sticky">
                  ここ、先週の自分そのもの。来週の1on1で田中さんに権限の線を見せて確認する。
                </div>
              )}
            </div>
          ))}
        </article>

        <aside className="rail-tools">
          <div className="tool-card panel">
            <div className="tc-h">
              <span className="k">✎</span> このページの操作
            </div>
            <div className="tool-actions">
              <div className="icon-btn">🖊</div>
              <div className="icon-btn">🏷</div>
              <div className="icon-btn">🔖</div>
            </div>
            <div className="muted" style={{ fontSize: 11.5, marginTop: 10, lineHeight: 1.5 }}>
              文章を選択するとハイライト・付箋を付けられます。
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
