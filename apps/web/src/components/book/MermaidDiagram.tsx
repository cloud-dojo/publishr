"use client";

import { useEffect, useRef, useState } from "react";

let _mermaidId = 0;

// LLM が出す Mermaid は編集記号の取りこぼしで壊れやすい。描画前に頻出の
// 破綻パターンだけ保守的に補正する（正しい図はできるだけ素通しする）。
export function sanitizeMermaid(src: string): string {
  let out = src.trim();
  // 1) エッジラベル |...| に丸括弧・波括弧・角括弧・# が素で入るとパースが割れる
  //    （例: -->|So What? (なぜ?)|）。未引用かつ構造記号を含むラベルだけ "..." で包む。
  out = out.replace(/\|([^|\n]+)\|/g, (m, label: string) => {
    const t = label.trim();
    if (!t || t.includes('"')) return m; // 既に引用済み／内部にクォート → 触らない
    if (/[()[\]{}#]/.test(t)) return `|"${t}"|`;
    return m;
  });
  // 2) 改行タグは自己終端 <br/> に寄せる（一部バージョンで <br> が不安定）。
  out = out.replace(/<br\s*>/gi, "<br/>");
  return out;
}

export function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;
    setFailed(false);

    import("mermaid").then(async ({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        theme: "neutral",
        fontFamily: "inherit",
        fontSize: 13,
        // パース失敗時に mermaid が body へエラー SVG を注入するのを抑止。
        suppressErrorRendering: true,
      });

      // まず原文で、壊れていれば保守補正版で再試行する。
      let svg: string | null = null;
      for (const src of [chart, sanitizeMermaid(chart)]) {
        try {
          const id = `mermaid-${++_mermaidId}`;
          ({ svg } = await mermaid.render(id, src));
          break;
        } catch {
          svg = null; // 次の候補へ
        }
      }

      if (cancelled) return;
      if (!svg || !containerRef.current) {
        setFailed(true);
        return;
      }

      containerRef.current.innerHTML = svg;
      // 固定の width/height 属性を外し、列幅いっぱい＋ページ高上限で
      // viewBox 比率を保って拡縮させる（小さすぎ／縦見切れの両方を防ぐ）。
      const svgEl = containerRef.current.querySelector("svg");
      if (svgEl) {
        svgEl.removeAttribute("height");
        svgEl.removeAttribute("width");
        svgEl.style.width = "100%";
        svgEl.style.height = "auto";
        svgEl.style.maxWidth = "100%";
      }
    }).catch(() => {
      if (!cancelled) setFailed(true);
    });

    return () => { cancelled = true; };
  }, [chart]);

  // パース不能でも生ソースは出さず、控えめなプレースホルダに留める。
  if (failed) {
    return (
      <div className="mermaid-error" role="img" aria-label="図解を表示できませんでした">
        （図は表示できませんでした）
      </div>
    );
  }
  return <div ref={containerRef} className="mermaid-diagram" />;
}
