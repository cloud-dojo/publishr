"use client";

import { useEffect, useRef, useState } from "react";

let _mermaidId = 0;

export function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const id = `mermaid-${++_mermaidId}`;
    let cancelled = false;

    import("mermaid").then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        theme: "neutral",
        fontFamily: "inherit",
        fontSize: 13,
      });
      return mermaid.render(id, chart);
    }).then(({ svg }) => {
      if (!cancelled && containerRef.current) {
        containerRef.current.innerHTML = svg;
        // SVG にレスポンシブ幅＋ページ高さ上限を付与。
        // 固定の height 属性を外し、CSS の max-height（--rd-page-h）で
        // viewBox 比率を保ったまま縮小させる（縦長図がページ枠で見切れるのを防ぐ）。
        const svgEl = containerRef.current.querySelector("svg");
        if (svgEl) {
          svgEl.removeAttribute("height");
          svgEl.style.maxWidth = "100%";
          svgEl.style.height = "auto";
        }
      }
    }).catch((e) => {
      if (!cancelled) setError(String(e));
    });

    return () => { cancelled = true; };
  }, [chart]);

  if (error) return <pre className="mermaid-error">{chart}</pre>;
  return <div ref={containerRef} className="mermaid-diagram" />;
}
