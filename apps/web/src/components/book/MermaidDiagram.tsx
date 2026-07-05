"use client";

import { useEffect, useRef, useState } from "react";

let _mermaidId = 0;

// これ未満のscaleまで縮めると本文フォント比で文字が潰れて読めなくなる目安（暫定値）。
const MIN_SCALE = 0.55;

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
  // 2) 空ノードラベル ("")/[""]/{""} は mermaid がパースに失敗する。最小の可視ラベルに置換
  //    （RACI表の空セル等で LLM が出しがち）。
  out = out.replace(/([([{])\s*""\s*([)\]}])/g, '$1"-"$2');
  // 3) 改行タグは自己終端 <br/> に寄せる（一部バージョンで <br> が不安定）。
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
      const svgEl = containerRef.current.querySelector("svg");
      if (svgEl) {
        svgEl.removeAttribute("height");
        svgEl.removeAttribute("width");
        // viewBox の自然サイズ（w×h・px相当）を取り、列幅に対して大きすぎるか判定する。
        const [, , w, h] = (svgEl.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
        const colW = containerRef.current.clientWidth; // ≒ 段組み1列の幅（≈400px）
        const pageH = parseFloat(
          getComputedStyle(containerRef.current).getPropertyValue("--rd-page-h"),
        );
        if (w > 0 && h > 0 && colW > 0 && pageH > 0) {
          // contain-fit: 縦横比を保ったまま列幅×ページ高の枠に必ず収める
          // （scale=min(横方向の縮小率, 縦方向の縮小率)。1超は拡大しない＝等倍上限）。
          const scale = Math.min(colW / w, pageH / h, 1);
          if (scale >= MIN_SCALE) {
            svgEl.style.width = `${w * scale}px`;
            svgEl.style.height = `${h * scale}px`;
            svgEl.style.maxWidth = "100%";
          } else {
            // 縮小しすぎると可読性が失われる複雑な図だけ、高さをページ高に合わせて
            // 等倍描画し、はみ出す横幅は .mermaid-diagram の overflow-x で横スクロールさせる
            // （プロンプト側の規律を守れなかった図への保険）。
            const dispH = h > pageH ? pageH : h;
            svgEl.style.height = `${dispH}px`;
            svgEl.style.width = `${w * (dispH / h)}px`;
            svgEl.style.maxWidth = "none";
          }
        } else {
          // pageH 未取得時など：列幅に収まる図として引き伸ばす（従来のフォールバック）。
          svgEl.style.width = "100%";
          svgEl.style.height = "auto";
          svgEl.style.maxWidth = "100%";
        }
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
