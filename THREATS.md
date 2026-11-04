# TrustVault threat model

This is an initial student threat model. Review it against the actual implementation and expand it with your own tests.

| Threat | Expected control | Test / evidence |
|---|---|---|
| Viewer guesses another document ID | Server checks membership and document permission on every download | `test_viewer_without_permission_is_denied` |
| Permission is revoked but old URL is reused | Download route re-reads active permission from database | `test_revoked_permission_is_denied` |
| Permission expires | Expiry is checked server-side | `test_expired_permission_is_denied` |
| User is not a project member | Membership check is required | `test_non_member_is_denied_even_with_permission_record` |
| User submits an unauthorized permission change | Owner/admin role and project ownership are checked | Add route-level negative tests |
| Malicious filename/path traversal | Stored file name is generated as UUID; original name is sanitized | Add upload tests with unusual filenames |
| Unsupported file type | Extension allowlist | Add tests for disallowed extensions |
| Oversized upload | Flask request limit and explicit size check | Add a 10 MB boundary test |
| CSRF form submission | Flask-WTF CSRF protection | Add route-level CSRF tests |
| Password database disclosure | Werkzeug password hashing | Verify stored value differs from plaintext |
| Audit row alteration | SHA-256 previous-hash chain | Add tests that mutate event fields and verify integrity |
| Brute-force login | Not implemented | Known limitation; add rate limiting before production |
| Malicious file content | Extension check only; no malware scanner | Known limitation; do not treat as safe for production |
| Full database rewrite by privileged attacker | Hash chain alone cannot prevent this | Export to independently controlled immutable storage |

## Security invariants

1. A project member is not automatically a document reader.
2. A viewer can download only when they are an active project member and hold an active, unexpired `read` or `edit` grant for that document.
3. A permission revocation takes effect on the next request.
4. A denied download is logged before the request is rejected.
5. A user cannot grant themselves permissions through the viewer routes.
6. The application never uses a user-supplied filename as the stored filesystem path.

## Manual verification checklist

- [ ] Log in as Viewer and try a document URL without permission.
- [ ] Grant read access, then confirm download succeeds.
- [ ] Revoke access and retry the exact same URL.
- [ ] Set a short expiry and verify access after expiry.
- [ ] Remove project membership and verify access is denied.
- [ ] Try to access another owner's project-management URL.
- [ ] Log in as Admin and run the audit-chain verification.
- [ ] Inspect the audit rows for both allowed and denied download events.
