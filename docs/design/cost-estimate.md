# Publishr LLM / Imagen Cost Estimate (G1-16 / C5.8)

> Updated: 2026-06-24. This document is a budget guard and planning estimate, not a verified billing statement.
> Real prices and actual token usage must be overwritten from GCP billing / Langfuse after live runs.

## 1. Current Product Premise

The old reservation model is no longer the cost baseline.

Current MVP baseline:

| Item | Current assumption |
|---|---|
| Weekly schedule | 3 runs / week |
| Books per run | 4 books |
| Weekly books | 12 books = 8 mainline + 4 serendipity |
| Writing timing | Every run writes all 4 books through to `published` |
| Reservation cap | Removed. It is not the cost guard anymore. |
| Shelf retention | Bookstore arrivals drop after 30 days. Books saved to library remain until explicit delete/drop. |
| Body size | Production target remains up to about 100 pages, but dev runs are intentionally short. |

Cost now scales mainly with **full body generation for all 12 weekly books**. Preview, planning, cover, and judge calls matter, but they are secondary compared with author/editor body loops.

## 2. Guard Price Assumptions

The code guard currently uses rough internal yen estimates in `agents/publishr_agents/llm/runtime.py`.

| Model bucket | Input | Output | Notes |
|---|---:|---:|---|
| Gemini Pro | JPY 350 / 1M tokens | JPY 1,050 / 1M tokens | Used for reader analysis, planning quality gates, author/editor loops |
| Gemini Flash | JPY 50 / 1M tokens | JPY 200 / 1M tokens | Used for lighter research/cover prompt style work |

These are conservative-enough development guard numbers, not a promise of actual Vertex AI pricing. C5.8 remains open until live billing and Langfuse usage are reconciled.

## 3. Weekly Cost Shape

| Pipeline area | Frequency | Main risk | Guard / mitigation |
|---|---:|---|---|
| STEP1 reader analysis | 1 / week | Medium Pro context | Reuse weekly profile for all three runs |
| STEP2 planning / scoring | 3 runs / week | Repeated Pro leader rounds | `PUBLISHR_MAX_ITERATIONS=3`; mock default |
| STEP3 casting | 3 runs / week | Medium Pro output | Fixed 4 books / run |
| STEP4 preview edit | 12 books / week | Pro author/editor loop | Dev keeps 1 round and short bodies |
| STEP5 cover | 12 covers / week | Imagen if enabled | `ENABLE_IMAGEN=false` in dev |
| Body author/editor loop | 12 books / week | Dominant cost source | 4 books / run cap; body page cap; weak-chapter-only revision |
| Eval / judge | On demand / CI-gated | Hidden repeated Pro calls | Keep live eval opt-in |

The budget conclusion changes from "reservation cap limits body cost" to:

- Weekly body cost is bounded by **3 runs x 4 books = 12 full books**.
- The most important abuse guard is the code-side run profile, not UI reservation state.
- Production is plausible under a JPY 10,000 hackathon budget only if live runs are limited, measured, and not repeated casually.

## 4. Runtime Guards

| Setting | Dev default | Prod default | Purpose |
|---|---:|---:|---|
| `PUBLISHR_RUN_PROFILE` | `dev` | `prod` | Dev is the safe default |
| `PUBLISHR_MAX_ITERATIONS` | 3 | 3 | Stops runaway loops |
| `PUBLISHR_MAX_BOOKS_PER_RUN` | 2 | 4 | Prod matches the current 4-book run contract |
| `PUBLISHR_BODY_PAGES_MIN` | 3 | 3 | Minimum body slice |
| `PUBLISHR_MAX_BODY_PAGES` | 5 | 100 | Dev keeps body generation tiny |
| `PUBLISHR_EDITOR_ROUNDS` | 1 | 3 | Production body quality loop ceiling |
| `ENABLE_IMAGEN` | false | true | Prevents accidental image spend in dev |
| `PUBLISHR_TIMEOUT_SECONDS` | 45 | 300 | Prevents hanging live calls |
| `PUBLISHR_MAX_ESTIMATED_COST_JPY` | 100 | 2,000 | Per-call preflight stop |

Additional production safety requirements:

- Trigger APIs must require Firebase auth and an allowlist for demo users.
- Trigger endpoints should enforce minimum interval / duplicate run protection.
- Langfuse and Cloud Logging must not store tokens, OAuth secrets, or full private document bodies.
- GCP budget alerts should be set at 50%, 90%, and 100%, but they are secondary protection. Code guards are primary.

## 5. C5.8 Measurement Checklist

Before declaring C5.8 complete:

1. Run one live minimal pipeline with explicit `PUBLISHR_RUN_PROFILE=dev`.
2. Record actual input/output tokens per role in Langfuse.
3. Compare Langfuse usage with GCP billing for Gemini / Imagen / grounding.
4. Run or simulate one production-shaped 4-book batch only when the dev sample is understood.
5. Replace this estimate with measured yen-per-run and projected yen-per-week.

Current status: **estimate updated for the reservation-free 12-book model; live full-pipeline measurement still pending**.
