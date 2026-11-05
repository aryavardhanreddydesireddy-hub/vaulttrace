# TrustVault Threat Model

This document identifies security threats in TrustVault, the controls implemented to reduce them, and the tests or evidence used to evaluate those controls.

## Threat Analysis

| Threat | Expected control | Test / evidence | Status |
|---|---|---|---|
| Viewer guesses another document ID | Server checks membership and document permission on every download | `test_viewer_without_permission_is_denied` | Verified |
| Permission is revoked but old URL is reused | Download route checks current active permission | `test_revoked_permission_is_denied` | Verified |
| Permission expires | Expiry is checked server-side | `test_expired_permission_is_denied` | Automated test passed |
| User is not a project member | Active project membership is required | `test_non_member_is_denied_even_with_permission_record` | Verified |
| Unauthorized permission change | Owner/admin authorization checks | Grant, revoke, approve and reject tests | Automated tests passed |
| Malicious filename | UUID storage and filename sanitization | `test_uploaded_filename_is_sanitized` | Automated test passed |
| Unsupported file type | File extension allowlist | `test_unsupported_file_extension_is_rejected` | Automated test passed |
| File extension does not match content | File signatures and format checks | Fake PDF and PNG rejection tests | Automated tests passed |
| Oversized upload | Flask request limit and explicit size check | `test_oversized_file_upload_is_rejected` | Automated test passed |
| Viewer attempts upload | Server-side role authorization | `test_viewer_cannot_upload_document` | Automated test passed |
| CSRF form submission | Flask-WTF CSRF protection | `test_post_without_csrf_token_is_rejected` | Automated test passed |
| Password database disclosure | Werkzeug password hashing | `test_password_is_stored_as_hash_not_plaintext` | Automated test passed |
| Audit row alteration | SHA-256 previous-hash chain | `test_audit_tampering_is_detected` | Automated test passed |
| Brute-force login | Flask-Limiter: 5 requests per minute per IP | `test_login_rate_limit_blocks_sixth_attempt` | Automated test passed |
| Malicious file content | Basic content validation | PDF and PNG validation tests | Partial protection; malware scanning not implemented |
| Full database rewrite | Independent immutable audit storage | Not implemented | Known limitation |

## Security Invariants

1. A project member is not automatically a document reader.
2. A viewer needs active membership and active, unexpired read or edit permission.
3. Permission revocation takes effect on the next request.
4. Denied downloads are logged.
5. Viewers cannot grant themselves permissions.
6. User-supplied filenames are not used as stored filesystem paths.
7. Authorization is checked server-side.
8. Inactive users cannot access protected documents.
9. Public registration always creates viewer accounts.
10. Uploaded files must pass extension and content checks.

## Manual Verification Checklist

- [x] Viewer access without permission denied.
- [x] Read access granted and download successful.
- [x] Revoked permission blocks the same URL.
- [ ] Verify access after permission expiry.
- [ ] Verify access after project membership removal.
- [ ] Test another owner's project-management URL.
- [x] Audit-chain verification.
- [x] Inspect allowed and denied download events.
- [x] Verify public registration creates viewer accounts.
- [x] Verify fake PDF and PNG uploads are rejected.

## Known Limitations and Future Improvements

- Add malware scanning.
- Perform additional expiry and membership-removal checks.
- Store audit exports in independently controlled immutable storage.
- Use shared rate-limit storage such as Redis for production deployments.
- Test file-content validation against additional formats and edge cases.

## Testing Summary

The automated test suite contains **23 tests, and all 23 passed** in the latest test run.

Tests cover permission enforcement, membership, unauthorized actions, password hashing, audit tampering, upload restrictions, filename sanitization, CSRF protection, public registration roles, file-content validation, and login rate limiting.

Manual verification has also confirmed permission revocation using the same document URL and audit-chain verification.

Further security testing is required before describing TrustVault as production-ready.