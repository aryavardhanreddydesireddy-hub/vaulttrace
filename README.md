# VaultTrace – Intelligent Document Access Control

A Flask-based document-sharing application demonstrating project membership, per-document permissions, access requests, protected downloads, and a hash-linked audit log.

## Important Before Submission

This is an educational project demonstration, not a security certification or a guarantee of production readiness. Run the application, test it, inspect the authorization code, change demo credentials, and document remaining limitations honestly.

## Live Application

**Live URL:** https://vaulttrace-q9bb.onrender.com/

The application is deployed using the Render Free Web Service plan for demonstration and project evaluation.

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

### 4. Configure environment variables

The application requires a secret key and an initial admin password.

```powershell
$env:SECRET_KEY = "your-generated-secret-key"
$env:ADMIN_PASSWORD = "your-unique-admin-password"
```

Use your own strong values in your terminal. Do not put real secret values in this README or commit them to GitHub.

### 5. Start the application

```powershell
python run.py
```

### 6. Open the application

Visit:

http://127.0.0.1:5000

If `py` is unavailable, use `python` instead.

## First Login

The database is created automatically on first start.

- Email: `admin@vaulttrace.local`
- Password: The value configured using the `ADMIN_PASSWORD` environment variable.

The initial admin account is created only when it does not already exist in the database. Keep the admin password private and never publish it.

For initial testing:

1. Sign in using the administrator account.
2. Create a project.
3. Register a test Viewer account.
4. Add the Viewer to the project using their registered email address.
5. Upload a sample document.
6. Grant the Viewer read permission.
7. Sign in using the Viewer account and test document access.

Public registration creates Viewer accounts. Administrator and project-owner privileges must not be granted through public registration.

## Permission Model

- Project membership alone does **not** grant document access.
- The document owner and admin currently have application-level full access.
- A viewer must be an active project member and have an active, unexpired permission for that exact document.
- `read` permits download.
- `edit` also permits download and is intended for future document-edit operations.
- Revocation sets the permission inactive. The download route checks the database on every request.
- An inactive membership blocks the viewer even if a permission record remains active.

## Tests

Activate the virtual environment and run:

```powershell
.venv\Scripts\activate
pytest -q
```

The permission tests use a temporary SQLite database and temporary upload directory.

A previous test run reported 23 passing tests. Run the test suite again after making code changes to confirm the current result.

Add tests for every new feature you implement.

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

### Current Deployment Configuration

VaultTrace is deployed on Render using its Free Web Service plan.

- Hosting: Render Free Web Service
- Application server: Gunicorn
- Database: SQLite
- Database location: `/tmp/vaulttrace.db`
- Upload directory: `/tmp/vaulttrace-uploads`

### Environment Variables

The following environment variables are configured through the Render dashboard:

- `SECRET_KEY`: Securely generated application secret.
- `ADMIN_PASSWORD`: Initial administrator password.
- `DATABASE_URL`: SQLite database location.
- `UPLOAD_FOLDER`: Temporary document upload location.

Never publish actual secret values or administrator credentials.

### Important Free-Plan Storage Limitation

The current free deployment uses temporary local storage.

Database records, user accounts, project information, permissions, audit events, and uploaded documents may be lost when the Render service restarts, sleeps, or redeploys.

Therefore:

- Use demonstration accounts and sample documents only.
- Do not upload confidential or personally sensitive documents.
- Do not rely on the live deployment for permanent data storage.
- Re-test the application after a restart or redeployment.

The current deployment is intended for educational demonstrations and project evaluation, not production use.

### Future Deployment Improvements

Persistent PostgreSQL database storage and cloud-based object storage can be integrated in a future version to improve data durability.

The current deployment does not include a persistent disk or external object-storage integration.

## Current Limitations

- The admin role is trusted by the application and can access all documents. A real organization may require stricter separation of duties.
- The hash chain detects some changes to stored audit rows, but it is not tamper-proof if an attacker can rewrite the entire database and recompute hashes. Stronger evidence requires independently controlled immutable storage and verification of all relevant event fields.
- File type validation is based on extension and basic content checks, not deep content inspection or malware scanning.
- `edit` permission is stored and enforced as an access level, but in-app document editing is not implemented.
- Password reset, MFA, email notifications, virus scanning, and object-storage integration are not included.
- The current rate-limiting configuration uses in-memory storage and is not shared across multiple application instances. A shared storage backend such as Redis would be preferable for a larger deployment.
- SQLite is intended for this learning project. Consider a managed database and durable file storage before using the application for real organizational data.
- The current Render Free deployment uses temporary local storage. Database records and uploaded documents are not guaranteed to survive service restarts, sleep, or redeployment.

## Project Documentation

See `THREATS.md` for the initial threat model and `PROMPTS.md` for the AI usage record. Keep both updated as development progresses.