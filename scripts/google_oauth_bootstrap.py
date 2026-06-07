"""Google OAuth 同意ブートストラップ（C1.1 STEP0 観測の実API用・対話的・1回だけ）。

ブラウザで Drive/Calendar/Tasks（読み取り専用）への同意を取り、リフレッシュトークンを
`.secrets/google_token.json`（gitignore 済）に保存する。以後 `run_observe.py --source google`
や `@pytest.mark.google` の live テストがこのトークンを使う。

  uv run python scripts/google_oauth_bootstrap.py

OAuth クライアント秘密の解決順:
  1) --client-secrets / PUBLISHR_GOOGLE_CLIENT_SECRETS（既定 .secrets/client_secret.json）の JSON
     ※ GCP コンソールで作成した「デスクトップ アプリ」OAuth クライアントの client_secret JSON を推奨
       （ループバック redirect を自動許可するため redirect URI 登録が不要）。
  2) 環境変数 GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET（installed クライアント設定を合成）。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from publishr_agents.observe.google_source import SCOPES, token_path

DEFAULT_CLIENT_SECRETS = ".secrets/client_secret.json"


def _flow(client_secrets: str):
    from google_auth_oauthlib.flow import InstalledAppFlow

    path = Path(client_secrets)
    if path.exists():
        print(f"client secrets: {path}")
        return InstalledAppFlow.from_client_secrets_file(str(path), SCOPES)

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        print("client secrets: env GOOGLE_OAUTH_CLIENT_ID/SECRET")
        config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        return InstalledAppFlow.from_client_config(config, SCOPES)

    raise SystemExit(
        f"OAuth クライアント秘密が見つかりません。\n"
        f"  - {client_secrets} にデスクトップ アプリの client_secret JSON を置く、または\n"
        f"  - 環境変数 GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET を設定してください。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Google OAuth 同意ブートストラップ（観測の実API用）")
    parser.add_argument(
        "--client-secrets",
        default=os.environ.get("PUBLISHR_GOOGLE_CLIENT_SECRETS", DEFAULT_CLIENT_SECRETS),
    )
    parser.add_argument("--port", type=int, default=0, help="ローカル受け口ポート（0=自動）")
    args = parser.parse_args()

    flow = _flow(args.client_secrets)
    print(f"スコープ: {SCOPES}")
    print("ブラウザで同意してください（デモ用 Google アカウントでログイン）…")
    creds = flow.run_local_server(port=args.port, prompt="consent")

    out = token_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n保存しました: {out}（gitignore 済）")
    print("確認: uv run python -m scripts.run_observe --user u_sakura --source google")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
