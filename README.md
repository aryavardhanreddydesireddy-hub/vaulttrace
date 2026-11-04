# TrustVault — Secure Document Sharing

A learning-focused Flask application demonstrating project membership, per-document permissions, access requests, protected downloads, and an append-only hash-linked audit log.

## Important Before Submission

This is a starter implementation, not a security certification or a guarantee of production readiness. Run the application, test it, inspect the authorization code, change the demo credentials, and document any remaining limitations honestly. Do not claim a feature works until you have verified it.

## Features Included

- Three account roles: `admin`, `owner`, and `viewer`.
- Project creation and member management.
- Document upload with an extension allowlist and 10 MB size limit.
- Per-document `read` or `edit` permissions, optional expiry, and revocation.
- Server-side authorization on protected document downloads.
- Viewer access requests with owner approval or rejection.
- Audit events for login attempts, permission changes, uploads, requests, and successful or denied downloads.
- SHA-256 hash links between audit events and a basic chain-integrity check.
- CSRF protection for forms, password hashing, and inactive-account checks.
- Automated tests for key permission rules.

## Requirements

- Python 3.10 or newer
- VS Code (optional)

## Run on Windows

Open the project folder in VS Code and open the terminal.

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Activate the environment

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the application

```powershell
python run.py
```

### 5. Open the application

Visit:

http://127.0.0.1:5000

If `py` is unavailable, use `python` instead.

## First Login

The database is created automatically on first start.

- Email: `admin@trustvault.local`
- Password: `REMOVED_OLD_DEMO_PASSWORD!`

These are demo credentials. Change the password before any public deployment by setting the `ADMIN_PASSWORD` environment variable. Never use the sample credentials on a public website.

For initial testing:

1. Register two test users: one Owner and one Viewer.
2. Sign in as Owner.
3. Create a project.
4. Add the Viewer by email.
5. Upload a document.
6. Grant the Viewer read permission.
7. Sign out and test the Viewer account.

## Permission Model

- Project membership alone does **not** grant document access.
- The document owner and admin currently have application-level full access.
- A viewer must be an active project member and have an active, unexpired permission for that exact document.
- `read` permits download.
- `edit` also permits download and is intended for future document-edit operations.
- Revocation sets the permission inactive. The download route checks the database on every request.
- A suspended or removed membership blocks the viewer even if a permission record remains active.

## Tests

Activate the virtual environment and run:

```powershell
.venv\Scripts\activate
pytest -q
```

The permission tests use a temporary SQLite database and temporary upload directory. Add tests for every new feature you implement.

## Git Workflow

Create your own repository and commit as you work.

Example:

```bash
git init
git add .
git commit -m "Create Flask application structure"
```

Continue making genuine commits after implementing and testing each feature. Never backdate commits or rewrite history to imply work that did not happen.

Keep the repository private while the challenge rules require it. Make it public only when permitted by the organizer.

## Deployment Notes

This app stores uploaded files on the local filesystem and uses SQLite by default. Many free hosting services use temporary filesystems, so uploaded files and SQLite data may disappear after a redeployment or restart.

For a reliable public deployment, configure:

1. A managed PostgreSQL database using `DATABASE_URL`.
2. Persistent object storage for uploaded documents, or a persistent disk attached to the web service.
3. A strong `SECRET_KEY` and unique `ADMIN_PASSWORD`.
4. HTTPS and the hosting provider's secure cookie settings.

Do not deploy with the sample admin password or debug mode enabled.

The repository includes a basic `render.yaml` as a starting point, not a one-click deployment guarantee. Verify the live URL in a private or incognito browser window.

## Current Limitations

- The admin role is trusted by the application and can access all documents. A real organization may require stricter separation of duties.
- The hash chain detects some changes to stored audit rows, but it is not tamper-proof if an attacker can rewrite the entire database and recompute hashes. Stronger evidence requires independently controlled immutable storage and verification of all relevant event fields.
- File type validation is based on extension, not deep content inspection or malware scanning.
- `edit` permission is stored and enforced as an access level, but in-app document editing is not implemented.
- Password reset, MFA, email notifications, virus scanning, rate limiting, and object-storage integration are not included.
- SQLite is intended for local development. Configure durable database and file storage before relying on a deployed instance.

## Project Documentation

See `THREATS.md` for the initial threat model and `PROMPTS.md` for the AI usage record. Keep both updated as development progresses.