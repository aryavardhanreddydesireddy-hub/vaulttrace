# TrustVault — Secure Document Sharing

A learning-focused Flask application demonstrating project membership, per-document permissions, access requests, protected downloads, and an append-only hash-linked audit log.

## Important before submission

This is a starter implementation, not a security certification or a guarantee of production readiness. You must run it, test it, inspect the authorization code, change the demo credentials, and document any remaining limitations honestly. Do not claim a feature works until you have verified it.

## Features included

- Three account roles: `admin`, `owner`, and `viewer`.
- Project creation and member management.
- Document upload with extension allowlist and 10 MB size limit.
- Per-document `read` or `edit` permissions, optional expiry, and revocation.
- Server-side authorization on protected document downloads.
- Viewer access requests with owner approval/rejection.
- Audit events for login attempts, permission changes, uploads, requests, and successful/denied downloads.
- SHA-256 hash links between audit events and a basic chain-integrity check.
- CSRF protection for forms, password hashing, and inactive-account checks.
- Automated tests for the key permission rules.

## Requirements

- Python 3.10 or newer
- VS Code (optional)

## Run on Windows

Open Command Prompt in this project folder:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py run.py
```

Open `http://127.0.0.1:5000`.

On systems where `py` is unavailable, use `python` instead.

## First login

The database is created automatically on first start.

- Email: `admin@trustvault.local`
- Password: `REMOVED_OLD_DEMO_PASSWORD!`

Change the password before any public deployment by setting the `ADMIN_PASSWORD` environment variable. Do not use the sample credentials on a public website.

Register two test users: one Owner and one Viewer. Sign in as Owner, create a project, add the Viewer by email, upload a document, and grant that Viewer read permission. Sign out and test the Viewer account.

## Permission model

- Project membership alone does **not** grant document access.
- The document owner and admin currently have application-level full access.
- A viewer must be an active project member and have an active, unexpired permission for that exact document.
- `read` permits download; `edit` also permits download and is intended for future document-edit operations.
- Revocation sets the permission inactive. The download route checks the database on every request.
- A suspended/removed membership blocks the viewer even if a permission record remains active.

## Tests

```bat
.venv\Scripts\activate
pytest -q
```

The tests use a temporary SQLite database and temporary upload directory. Add tests for every new feature you implement.

## Git workflow

Create your own repository and commit as you work. Example:

```bash
git init
git add .
git commit -m "Create Flask application structure"
```

Continue making real commits after implementing and testing each feature. Never backdate commits or rewrite history to imply work that did not happen. Keep the repository private while the challenge rules require it; make it public only when permitted by the organizer.

## Deployment notes

This app stores uploaded files on the local filesystem and uses SQLite by default. Many free hosting services use temporary filesystems, so uploaded files and SQLite data may disappear on redeploy/restart. For a reliable public deployment, configure:
1. A managed PostgreSQL database (change `DATABASE_URL` to the provider's SQLAlchemy URL; for some providers change `postgres://` to `postgresql://`).
2. Persistent object storage for uploaded documents, or a persistent disk attached to the web service.
3. A strong `SECRET_KEY` and unique `ADMIN_PASSWORD`.
4. HTTPS and the hosting provider's secure cookie settings.

Do not deploy with the sample admin password or debug mode enabled. This repository includes a basic `render.yaml` as a starting point, not a one-click guarantee. Verify the live URL in a private/incognito window.

## Current limitations to understand

- The admin role is trusted by the application and can access all documents. A real organization may require stricter separation of duties.
- The hash chain detects some changes to stored audit rows, but it is not tamper-proof if an attacker can rewrite the entire database and recompute hashes. For stronger evidence, export events to independently controlled immutable storage and include all event fields in verification.
- File type validation is based on extension, not deep content inspection or malware scanning.
- `edit` permission is stored and enforced as an access level, but in-app document editing is not implemented.
- No password reset, MFA, email notifications, virus scanning, rate limiting, or object-storage integration is included.
- This starter uses SQLite for local development. Configure durable database and file storage before relying on a deployed instance.

## Project documentation

See `THREATS.md` for the initial threat model and `PROMPTS.md` for the AI-work log. Update both as you work.
