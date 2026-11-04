# TrustVault Threat Model

This document identifies security threats in TrustVault, the controls implemented to reduce them, and the tests or evidence used to evaluate those controls.

## Threat Analysis

| Threat | Expected control | Test / evidence | Status |
|---|---|---|---|
| Viewer guesses another document ID | Server checks membership and document permission on every download | `test_viewer_without_permission_is_denied` | Verified |
| Permission is revoked but old URL is reused | Download route checks current active permission | `test_revoked_permission_is_denied`; reused URL manually tested | Verified |
| Permission expires | Expiry is checked server-side | `test_expired_permission_is_denied` | Automated test passed |
| User is not a project member | Active project membership is required | `test_non_member_is_denied_even_with_permission_record` | Verified |
| User submits an unauthorized permission change | Owner/admin authorization and project ownership checks | Grant, revoke, approve and reject negative tests | Automated tests passed |
| Malicious filename or path traversal | Stored filename is generated using a UUID; original filename is sanitized | `test_uploaded_filename_is_sanitized` | Automated test passed |
| Unsupported file type | File extension allowlist | `test_unsupported_file_extension_is_rejected` | Automated test passed |
| Oversized upload | Flask request limit and explicit size check | `test_oversized_file_upload_is_rejected` | Automated test passed |
| Viewer attempts document upload | Server-side role authorization | `test_viewer_cannot_upload_document` | Automated test passed |
| CSRF form submission | Flask-WTF CSRF protection | Route-level CSRF tests still required | Protection configured; testing pending |
| Password database disclosure | Werkzeug password hashing | `test_password_is_stored_as_hash_not_plaintext` | Automated test passed |
| Audit row alteration | SHA-256 previous-hash chain | `test_audit_tampering_is_detected` | Automated test passed |
| Brute-force login | No rate limiting currently implemented | No protection test available | Known limitation |
| Malicious file content | Extension validation only; no malware scanner | Malware scanning is not implemented | Known limitation |
| Full database rewrite by privileged attacker | Hash chain alone cannot prevent complete database rewriting | Independent immutable audit storage is not implemented | Known limitation |

## Security Invariants

1. A project member is not automatically a document reader.
2. A viewer can download a document only when they are an active project member and have active, unexpired `read` or `edit` permission.
3. Permission revocation takes effect on the next request.
4. A denied download is logged before the request is rejected.
5. A viewer cannot grant themselves permissions through viewer-level routes.
6. The application does not use a user-supplied filename as the stored filesystem path.
7. Authorization is checked on the server, not only through the user interface.
8. Inactive users cannot access protected documents.

## Manual Verification Checklist

- [x] Log in as Viewer and try a document URL without permission.
- [x] Grant read access and confirm that the download succeeds.
- [x] Revoke access and retry the exact same URL.
- [ ] Set a short expiry and verify access after the expiry time.
- [ ] Remove project membership and verify that access is denied.
- [ ] Try to access another owner's project-management URL.
- [x] Log in as Admin and run the audit-chain verification.
- [x] Inspect audit rows for allowed and denied download events.

## Known Limitations and Future Improvements

- Add login rate limiting to reduce repeated password-guessing attempts.
- Add malware scanning before uploaded files are made available.
- Add route-level CSRF protection tests.
- Verify expiry and membership removal through additional manual checks.
- Store audit exports in independently controlled, immutable storage to provide stronger protection against privileged database modification.
- Consider validating uploaded file contents instead of relying only on file extensions.

## Testing Summary

The current automated test suite contains 18 tests, and all 18 passed in the latest test run.

The tests cover permission enforcement, revoked and expired permissions, project membership, unauthorized permission changes, password hashing, audit-event tampering, unsupported file extensions, filename sanitization, oversized uploads, and viewer upload restrictions.

Manual verification has also confirmed permission revocation using the same document URL and audit-chain verification.

Further security testing is required before describing TrustVault as production-ready.
