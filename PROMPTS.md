# AI-assisted development log

This log records actual AI-assisted development activities, the checks performed, and the corrections made during TrustVault development.

## Entry 1 — 2026-11-04 — Document access authorization review

- **Tool:** ChatGPT
- **What I asked:** Review the TrustVault authorization logic and help verify whether users without document permissions can access documents.
- **What it produced:** Suggested reviewing the permission checks for document ownership, active membership, permission status, and expiry.
- **What was wrong or incomplete:** Code review alone could not prove that every unauthorized access attempt was blocked.
- **What I changed:** Added and ran tests for viewers without permission, revoked permissions, expired permissions, non-members, and inactive owners.
- **Verification:** The related authorization tests passed as part of the automated test suite.
- **Commit:** Pending — add the actual commit URL after committing.

## Entry 2 — 2026-11-04 — Audit trail integrity testing

- **Tool:** ChatGPT
- **What I asked:** Help test whether TrustVault's SHA-256 audit hash chain detects changes to existing audit events.
- **What it produced:** Suggested creating an audit event, modifying its stored details, and checking the audit verification result.
- **What was wrong or incomplete:** The initial test assertion did not match the actual verification message displayed by the application.
- **What I changed:** Checked the application's actual verification output and corrected the test assertion.
- **Verification:** `test_audit_tampering_is_detected` passed. The test confirmed that changing an event is detected by the hash-chain verification.
- **Commit:** Pending — add the actual commit URL after committing.

## Entry 3 — 2026-11-04 — Secure document upload handling

- **Tool:** ChatGPT
- **What I asked:** Review the document upload route in `app.py` and identify possible security and error-handling problems.
- **What it produced:** Recommended retaining server-side authorization, validating extensions and file sizes, sanitizing filenames, generating random storage names, and cleaning up a saved file if the database operation fails.
- **What was wrong or incomplete:** Extension validation alone does not verify the actual contents of an uploaded file or detect malware.
- **What I changed:** Updated the upload route with error handling and cleanup for failed database operations.
- **Verification:** Existing automated tests continued to pass after the route update.
- **Commit:** Pending — add the actual commit URL after committing.

## Entry 4 — 2026-11-04 — Upload security test development

- **Tool:** ChatGPT
- **What I asked:** Help create tests for unsupported file extensions, unsafe filenames, oversized files, and viewer upload restrictions.
- **What it produced:** Suggested individual pytest tests using the Flask test client and temporary test database.
- **What was wrong or incomplete:** The tests needed to be checked against the actual application's routes, response codes, and database behavior.
- **What I changed:** Added the tests to `tests/test_permissions.py` and checked their results individually.
- **Verification:** The unsupported-extension test, filename-sanitization test, oversized-file test, and viewer-upload test each passed. The complete test suite reached 18 passing tests.
- **Commit:** Pending — add the actual commit URL after committing.

## Entry 5 — 2026-11-04 — Threat model and security documentation

- **Tool:** ChatGPT
- **What I asked:** Help update `THREATS.md` to reflect the security tests completed and distinguish verified protections from pending checks and known limitations.
- **What it produced:** Suggested an updated threat analysis table, security invariants, manual verification checklist, and known limitations.
- **What was wrong or incomplete:** The earlier documentation still reported only seven passing tests and marked several newly tested protections as pending.
- **What I changed:** Updated the document to report 18 passing tests and revised the status of the tested security controls. Kept untested manual checks and known limitations clearly identified.
- **Verification:** Reviewed the Markdown preview and confirmed that the threat analysis table displays correctly.
- **Commit:** Pending — add the actual commit URL after committing.

## Development note

AI suggestions were treated as recommendations rather than automatically trusted code. Changes were checked against the actual Flask application and pytest results. The project is still undergoing security testing and should not be described as production-ready.
