"""P2 MiniLoop 実行CLI（実Vertex Gemini）。

H2の再現性成果物: 誰でも `uv run python -m scripts.run_miniloop` で再実行でき、
却下→再提出→採用（escalate）の遷移を確認できる。**実LLM・課金あり**。

Langfuse キーは env を優先し、無ければ Secret Manager から best-effort 取得（gcloud）。
"""

from __future__ import annotations

import argparse
import os
import subprocess


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def _load_langfuse_from_secret_manager() -> None:
    """env に Langfuse キーが無ければ Secret Manager から取得（失敗は無視）。"""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    names = {
        "LANGFUSE_PUBLIC_KEY": "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY": "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST": "LANGFUSE_HOST",
    }
    for env_name, secret in names.items():
        if os.environ.get(env_name):
            continue
        try:
            value = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", "--secret", secret, "--project", project],
                capture_output=True, text=True, timeout=30,
            )
            if value.returncode == 0 and value.stdout.strip():
                os.environ[env_name] = value.stdout.strip()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="P2 MiniLoop（実Vertex）実行")
    parser.add_argument("--threshold", type=int, default=70, help="承認スコア閾値（高くすると差し戻しを誘発）")
    parser.add_argument("--theme", default=None, help="調査テーマ（省略時は既定の佐倉美咲テーマ）")
    args = parser.parse_args()

    _ensure_vertex_env()
    _load_langfuse_from_secret_manager()

    from publishr_agents.observability import trace_miniloop
    from publishr_agents.vertex import run_miniloop

    print(f"== MiniLoop 実行（project={os.environ.get('GOOGLE_CLOUD_PROJECT')} / region={os.environ.get('GOOGLE_CLOUD_LOCATION')} / threshold={args.threshold}）==")
    kwargs = {"threshold": args.threshold}
    if args.theme:
        kwargs["theme"] = args.theme
    result = run_miniloop(**kwargs)

    print("\n-- 企画リーダーの差し戻し遷移（却下→再提出→採用）--")
    for v in result["verdict_history"]:
        print(f"  R{v['round']}: score={v['score']} decision={v['decision']}")
    print(f"\nrounds={result['rounds']} forced_approve={result['forced_approve']}")

    plan = result.get("approvedPlan") or {}
    print(f"\n承認企画タイトル: {plan.get('tentativeTitle', '(なし)')}")
    print(f"差別化(diffFromMarket): {str(plan.get('diffFromMarket', ''))[:160]}")

    sub = result.get("subMarket") or ""
    print(f"\n-- 調査サブ(grounding)抜粋 --\n{sub[:400]}")

    status = trace_miniloop(result)
    print(f"\nLangfuse: {status}")

    ok = bool(result.get("approvedPlan")) and bool(result["verdict_history"])
    print(f"\nH2判定: {'PASS（approvedPlan＋遷移あり）' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
