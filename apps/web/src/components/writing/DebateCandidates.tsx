import type { PlanningCandidate, RejectLogEntry } from "@publishr/shared-schema";

export function DebateCandidates({
  entries,
  candidates = [],
  approvedPlanIds = [],
}: {
  entries: RejectLogEntry[];
  candidates?: PlanningCandidate[];
  approvedPlanIds?: string[];
}) {
  const round2 = entries.filter((e) => e.round === 2);
  const shown = round2.length ? round2 : entries;
  const planByCandidate = new Map(candidates.map((c) => [c.candidate, c.planId]));
  return (
    <div className="debate">
      {shown.map((e, i) => (
        <div key={i} className={`cand ${e.verdict === "採用" ? "win" : "lose"}`}>
          <div className="cd-h">{e.persona}</div>
          「{e.candidate}」
          <div className="verdict">
            {e.verdict === "採用" ? "▲" : "▽"} {e.verdict}：{e.reason}
          </div>
          {planByCandidate.get(e.candidate) && (
            <div className="verdict">
              plan: {planByCandidate.get(e.candidate)}
              {approvedPlanIds.includes(planByCandidate.get(e.candidate) ?? "") ? " / 入荷対象" : ""}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
