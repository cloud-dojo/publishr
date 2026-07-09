"""Dump Mode A prompt-review artifacts step by step.

This CLI is intentionally separate from `run_mode_a.py`: it runs the same
offline-first Mode A set flow, but keeps every intermediate outlet as JSON and
adds a compact Markdown review sheet for human prompt tuning.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from publishr_schema import PlanProposal, load_users

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts" / "prompt-review"
JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def _resolve_now(now_arg: str | None, source: str) -> datetime:
    if now_arg:
        value = now_arg[:-1] + "+00:00" if now_arg.endswith("Z") else now_arg
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=JST)
    return datetime.now(JST) if source == "google" else DEMO_NOW


def _build_source(source: str) -> Any:
    if source == "fixture":
        from publishr_agents.observe import FixtureObservationSource

        return FixtureObservationSource()
    if source == "google":
        from publishr_agents.observe.google_source import GoogleObservationSource

        return GoogleObservationSource()
    raise SystemExit(f"unknown --source={source!r}: expected fixture or google")


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True)
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _safe_id(value: str | None, fallback: str) -> str:
    raw = value or fallback
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw)


def _compact(text: Any, limit: int = 160) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "..."


def _review_markdown(report: dict[str, Any]) -> str:
    profile = report["readerProfile"]
    current = profile.get("currentWork", {})
    planning = report["planning"]
    verdict = planning.get("planSetVerdict") or {}
    reject_log = planning.get("rejectLog") or []
    books = report["books"]
    manifest = report["manifest"]
    llm = manifest["llm"]

    lines: list[str] = [
        "# Prompt Review",
        "",
        "## Run",
        "",
        f"- user: `{manifest['userId']}`",
        f"- source: `{manifest['source']}`",
        f"- themeKind: `{manifest['themeKind']}`",
        (
            "- llm: "
            f"reader=`{llm['reader']}`, "
            f"planning/casting=`{llm['planning']}`, "
            f"preview=`{llm['preview']}`, "
            f"cover=`{llm['cover']}`"
        ),
        "",
        "## Review Checklist",
        "",
        "- [ ] STEP1 reader profile is concrete enough for prompt tuning",
        "- [ ] STEP2 four plans differ in role, payoff, and tone",
        "- [ ] STEP2 rejectLog explains rejection and later improvement",
        "- [ ] STEP3 author persona voice and format fit the selected plan",
        "- [ ] STEP4 title, reason, and agenda fit the reader's current moment",
        "- [ ] STEP5 cover direction matches the book's role and emotional tone",
        "",
        "## STEP1 Reader Profile",
        "",
        f"- currentSituation: {_compact(current.get('currentSituation'))}",
        f"- activeWorkThemes: {', '.join(current.get('activeWorkThemes') or [])}",
        f"- challenges: {', '.join(current.get('challenges') or [])}",
        "",
        "Reviewer notes:",
        "",
        "- keep:",
        "- fix:",
        "- risk:",
        "- example:",
        "",
        "## STEP2 Planning Set",
        "",
        (
            f"- verdict: `{verdict.get('decision')}` "
            f"score=`{verdict.get('score')}` rounds=`{planning.get('rounds')}`"
        ),
        f"- rejectLog entries: {len(reject_log)}",
        "",
    ]

    if reject_log:
        lines.extend(["### Reject Log", ""])
        for item in reject_log:
            below = ", ".join(item.get("belowFloor") or [])
            lines.append(
                f"- round {item.get('round')}: belowFloor=[{below}] "
                f"feedback={_compact(item.get('rejectionFeedback'), 220)}"
            )
        lines.append("")

    lines.extend(["### Approved Plans", ""])
    for book in books:
        plan = book["plan"]
        lines.extend(
            [
                f"#### {plan.get('proposalId')}: {plan.get('tentativeTitle')}",
                "",
                f"- theme: {_compact(plan.get('theme'))}",
                f"- role: {_compact(plan.get('themeRole'))} / "
                f"{_compact(plan.get('bookRole'))}",
                f"- readerSituation: {_compact(plan.get('readerSituation'), 220)}",
                f"- diffFromMarket: {_compact(plan.get('diffFromMarket'), 220)}",
                "",
            ]
        )

    lines.extend(["## STEP3-5 Book Outlets", ""])
    for book in books:
        plan = book["plan"]
        persona = (book.get("personas") or [{}])[0]
        shelved = (book.get("shelved") or [{}])[0]
        draft = shelved.get("bookDraft") or {}
        lines.extend(
            [
                f"### {draft.get('title') or plan.get('tentativeTitle')}",
                "",
                f"- planId: `{plan.get('proposalId')}`",
                (
                    f"- author: {persona.get('name', '')} "
                    f"({_compact(persona.get('voiceStyle'))} / "
                    f"{_compact(persona.get('format'))})"
                ),
                f"- deliveryReason: {_compact(draft.get('deliveryReason'), 240)}",
                f"- problemToSolve: {_compact(draft.get('problemToSolve'), 200)}",
                f"- coverVariant: `{shelved.get('coverVariant')}`",
                f"- coverPrompt: {_compact(shelved.get('coverPrompt'), 240)}",
                "",
                "Reviewer notes:",
                "",
                "- keep:",
                "- fix:",
                "- risk:",
                "- example:",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def run_review_dump(args: argparse.Namespace) -> Path:
    from publishr_agents.casting import cast_author
    from publishr_agents.cover import design_covers
    from publishr_agents.observe import collect_observation
    from publishr_agents.planning import run_planning_set
    from publishr_agents.preview import run_preview
    from publishr_agents.reader import analyze_reader

    if (
        "vertex" in (args.reader_llm, args.llm, args.preview_llm, args.cover_llm)
        or args.enable_imagen
    ):
        _ensure_vertex_env()

    users = {user.id: user for user in load_users()}
    user = users.get(args.user)
    if user is None:
        raise SystemExit(f"user not found: {args.user}")

    now = _resolve_now(args.now, args.source)
    run_id = args.run_id or datetime.now(JST).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / run_id
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    source = _build_source(args.source)
    observation = collect_observation(user, now=now, source=source)
    profile = analyze_reader(observation, user=user, llm=args.reader_llm)
    planning = run_planning_set(
        profile,
        theme_kind=args.theme_kind,
        threshold=args.threshold,
        llm=args.llm,
    )

    _write_json(raw_dir / "00_observation_bundle.json", observation)
    _write_json(raw_dir / "01_reader_profile.json", profile)
    _write_json(raw_dir / "02_theme_assignment_set.json", planning.get("themeAssignmentSet"))
    _write_json(raw_dir / "02_research.json", planning.get("research", {}))
    _write_json(raw_dir / "02_plan_set.json", planning.get("planSet"))
    _write_json(raw_dir / "02_plan_set_verdict.json", planning.get("planSetVerdict"))
    _write_json(raw_dir / "02_reject_log.json", planning.get("rejectLog", []))

    favorites = list(user.favorite_authors or [])
    books: list[dict[str, Any]] = []
    raw_plans = (planning.get("planSet") or {}).get("plans") or []
    for idx, raw_plan in enumerate(raw_plans, start=1):
        plan = PlanProposal.model_validate(raw_plan)
        plan_id = _safe_id(plan.proposal_id, f"plan_{idx}")
        casting = cast_author(
            plan,
            reader_profile=profile,
            favorite_authors=favorites,
            llm=args.llm,
        )
        chosen = []
        if casting.chosen:
            chosen = [
                casting.chosen.model_copy(
                    update={"persona_id": f"cast_{plan.proposal_id}"}
                )
            ]
        drafts = run_preview(
            plan,
            chosen,
            reader_profile=profile,
            limit=1,
            llm=args.preview_llm,
        )
        shelved = design_covers(
            drafts,
            chosen,
            llm=args.cover_llm,
            enable_imagen=args.enable_imagen,
        )

        book_report = {
            "plan": _to_jsonable(plan),
            "casting": _to_jsonable(casting),
            "personas": _to_jsonable(chosen),
            "drafts": _to_jsonable(drafts),
            "shelved": _to_jsonable(shelved),
        }
        books.append(book_report)
        _write_json(raw_dir / f"03_author_casting_{idx:02d}_{plan_id}.json", casting)
        _write_json(raw_dir / f"04_book_draft_{idx:02d}_{plan_id}.json", drafts)
        _write_json(raw_dir / f"05_shelved_book_{idx:02d}_{plan_id}.json", shelved)

    manifest = {
        "userId": user.id,
        "source": args.source,
        "collectedAt": now.isoformat(),
        "themeKind": args.theme_kind,
        "threshold": args.threshold,
        "llm": {
            "reader": args.reader_llm,
            "planning": args.llm,
            "preview": args.preview_llm,
            "cover": args.cover_llm,
            "imagen": bool(args.enable_imagen),
        },
        "rawDir": str(raw_dir),
        "bookCount": len(books),
    }
    report = {
        "manifest": manifest,
        "readerProfile": _to_jsonable(profile),
        "planning": planning,
        "books": books,
    }
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "review_payload.json", report)
    (out_dir / "review.md").write_text(_review_markdown(report), encoding="utf-8")
    return out_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dump step-by-step Mode A prompt outlets for human review."
    )
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument(
        "--llm",
        default="mock",
        choices=["mock", "vertex"],
        help="STEP2 planning + STEP3 casting",
    )
    parser.add_argument("--preview-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--cover-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--enable-imagen", action="store_true")
    parser.add_argument("--theme-kind", default="honmei", choices=["honmei", "serendipity"])
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument(
        "--now",
        default=None,
        help="ISO datetime; fixture default is fixed demo time",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--run-id",
        default=None,
        help="Stable output folder name for repeatable reviews",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = run_review_dump(args)
    print(f"Prompt review dump written: {out_dir}")
    print(f"Review sheet: {out_dir / 'review.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
