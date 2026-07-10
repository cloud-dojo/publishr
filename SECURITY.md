# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately via GitHub's **"Report a vulnerability"** flow on this
repository (Security → Advisories → *Report a vulnerability*):
https://github.com/cloud-dojo/publishr/security/advisories/new

We aim to acknowledge reports within a few business days.

## Notes on secrets and keys

- This repository is a hackathon showcase. The client-side Firebase Web
  configuration values (`NEXT_PUBLIC_*` in `apphosting.yaml`) are **intended to
  be public** — they ship to the browser by design and are restricted at the
  Google Cloud project level (HTTP referrer / API restrictions). They are not
  secrets.
- Server-side secrets (OAuth client secret, webhook tokens, etc.) are managed
  via **Google Secret Manager** and are **not** committed to this repository.
- If you believe a genuinely sensitive credential has been committed, please
  report it privately using the flow above rather than opening a public issue.
