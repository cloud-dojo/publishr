import type { RejectLogEntry } from "@publishr/shared-schema";

export function DebateCandidates({ entries }: { entries: RejectLogEntry[] }) {
  const round2 = entries.filter((e) => e.round === 2);
  const shown = round2.length ? round2 : entries;
  return (
    <div className="debate">
      {shown.map((e, i) => (
        <div key={i} className={`cand ${e.verdict === "採用" ? "win" : "lose"}`}>
          <div className="cd-h">{e.persona}</div>
          「{e.candidate}」
          <div className="verdict">
            {e.verdict === "採用" ? "▲" : "▽"} {e.verdict}：{e.reason}
          </div>
        </div>
      ))}
    </div>
  );
}
