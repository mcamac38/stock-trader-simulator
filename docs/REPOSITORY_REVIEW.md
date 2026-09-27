# Capstone repository review

Reviewed on 2026-09-26 against `main` commit `a3573464dfc9baf28c0e3cbd038bba97a4826d49`.

Scope: source inspection, ZIP comparison, syntax parsing without execution, and a targeted security/hygiene check. No AWS services were contacted, no credentials were tested, and no application/database integration test was performed. After comparison, the project lead confirmed that `SRE_Stock_Sim_Current` was the final backend used to run the capstone. This change restores that source as `backend/app.py` with LF line endings. It does not alter frontend files, deployment paths, or backend behavior relative to the supplied final file.

## Backend provenance and comparison

| Input | SHA-256 | Result |
| --- | --- | --- |
| Baseline `backend/app.py` at the reviewed commit | `dc6692ad0b2059047c5407dbb1d0f57e2bb46dc6036f54065c8092622d0bba59` | 64,415 bytes; syntax parsing fails |
| `stock-trader-simulator-main(1).zip` → `backend/app.py` | Same as live backend | Byte-for-byte identical |
| `SRE_Stock_Sim_Current(1).py` | `cbaed184dc6ad34e3c3c8bfe3d1bb0318c9ff7492211aee68696188bf6897c85` | 68,484 bytes; syntax parsing passes |
| `SRE_Stock_Sim_Current(2).py` | Same as uploaded `(1)` | Byte-for-byte identical to `(1)` |

Every file in the uploaded ZIP matched its corresponding file in the live checkout. Both backend variants declare the same 23 Flask route decorators, covering the same application areas. The uploaded file did not exactly match any of the 16 `backend/app.py` revisions on the checked-out main history, even after normalizing line endings. This supports common code lineage but does not establish chronology or prove which file was deployed to EC2.

The live backend has three syntax blockers: an unterminated CORS string at line 763, an unclosed parenthesis at line 1338, and incorrect decorator indentation at line 1486. Correcting only those three in an in-memory analysis copy allows syntax parsing to complete; the original source was left intact.

### Meaningful differences in the separately uploaded file

| Area | Difference from committed `app.py` | Implication |
| --- | --- | --- |
| Syntax | Repairs the three parsing blockers | Parseable does not mean integration-tested |
| Market calendar | Fixes `close.date` to `close_date`; applies special hours; adds weekend handling | More complete scheduling behavior |
| Database schema | Reads and writes `market_hours.allow_weekend_trading` | Requires a column not referenced by the committed version; no matching migration is supplied |
| Admin behavior | Lets admins bypass a closed market on weekends | Can also bypass a weekend full-day closure; intended policy needs confirmation |
| Portfolio | Adds `company_name` to holdings and sorts by company name | Response contents and ordering change |
| Sell transaction | Replaces the position `SELECT ... FOR UPDATE` with an unlocked read and later writes a computed quantity | Potential concurrent-sale inconsistency; do not overwrite the existing locking behavior blindly |
| Sell response | Returns `remaining_quantity` and `transaction_id` instead of nested `position` | Verify consumers before choosing a canonical implementation |
| CORS | Completes the configuration but permits only GET, POST, OPTIONS | Admin PUT requests are absent from its allowed-method list; gateway behavior has not been verified |
| Market status | Corrects `tzname` to `tz_name` | Fixes the fallback timezone variable |
| Authentication | Retains username-token fallback, development JWT secret default, and demo credentials | Syntax repair did not harden authentication |

`db_get_portfolio_history` is moved within the uploaded file; moving it alone does not establish a new feature. Line-ending and whitespace differences were normalized for the behavioral comparison.

### Final-version confirmation

The project lead explicitly confirmed during this review: “The SRE_Stock_Sim_Current was the final backend code file we used to run the application.” That confirmation establishes which supplied source to restore for this capstone. The source comparison alone could not establish deployment provenance. No access to the historical EC2 host was used to independently verify it.

The restored source preserves the final file's behavior, including the known authentication fallback and changed sell implementation. Those issues require deliberate follow-up fixes, rather than silently blending features from different snapshots. Verify the matching database schema, especially `market_hours.allow_weekend_trading`, before attempting a deployment.

### Additional attached source files

A subsequent batch included 13 frontend files plus another file named `app.py`. That `app.py` is **not** the confirmed final source: it has 983 lines, fails syntax parsing at line 372, and matches historical backend revision `dca2dd0` after line-ending normalization. It was not selected.

The attached `withdraw.html`, `admin-market-hours.html`, `admin-market-schedule.html`, `deposit.html`, and `register.html` match the live versions after line-ending normalization. The other eight frontend files differ. Several lack features present in GitHub: the attached buy and portfolio pages contain chart placeholders, login lacks the admin-role redirect, the index lacks calculated market fields, and the attached API helper calls older portfolio routes. These attachments were not used to overwrite the live frontend.

## Security and hygiene findings

These findings apply to the inspected source, not a verified running service. Secret values are intentionally omitted.

| Priority | Finding and evidence | Follow-up |
| --- | --- | --- |
| Critical | `backend/app.py:get_current_user` accepts a database username as the bearer value after JWT decoding fails; the uploaded candidate retains this | Remove the legacy fallback in the selected canonical backend; verify missing, malformed, expired, and forged tokens return 401 |
| High | `JWT_SECRET` falls back to a publicly committed development value in both variants | Require an explicit strong secret; rotate it if that default was ever used in a deployed environment |
| High | Plaintext demo password literals remain in `app.py`, `app.txt`, `app1.0.py`, and `app2.0.py`; registration logs both password fields in `frontend/Trading_System/pages/register.html:200` | Remove demo credentials and password logging; rotate any credential that was real or reused |
| High | Uploaded sell implementation removes the position row lock | Preserve transaction correctness when reconciling versions and test concurrent sells |
| Medium | Browser bearer tokens live in `localStorage`; logout removes only the local copy | Review script-injection exposure and session/revocation requirements before deployment |
| Medium | Many API errors return raw exception strings; `/dbcheck` is publicly routed | Return generic errors to clients and restrict operational diagnostics |
| Medium | The uploaded CORS configuration omits PUT despite admin PUT routes | Reconcile frontend origins and methods with the actual gateway configuration |
| Medium | Requirements omit PyJWT and Gunicorn and are unpinned | Create and verify complete reproducible dependencies for the restored backend |
| Medium | CI supplies `DATABASE_URL`, but the app reads separate `DATABASE_*` variables; lint, format, and Bandit checks use `|| true` | Align test configuration and make relevant quality checks enforceable; current CI is not evidence of production readiness |
| Low | `.gitignore` spells `__pycache__/` incorrectly and combines the Thumbs.db entry with another fragment | Correct ignore rules and include local environment variants while allowing a sanitized example |
| Low | Earlier backend/frontend variants and teammate source files coexist with active pages | Inventory references and preserve team credit before moving historical files; verify Amplify paths before reorganizing |

A targeted scan of current tracked source found no AWS access-key IDs matching common AKIA/ASIA formats and no private-key PEM headers. This is not a full secret scan or a review of all historical commits. Public API/Amplify addresses are deployment identifiers, not secret credentials by themselves.

The existing automated test checks `/health` only. Importing the backend also starts a price-update thread, so a health test should not be treated as isolated from database activity without additional controls. Syntax parsing here did not import or execute either backend.

## Recommended cleanup order

1. Review the README's team-lead contribution wording and historical deployment description.
2. The final backend has been identified by the project lead and restored. Keep the newer SRE project's changes separate.
3. Reconcile transaction locking and verify the restored backend against its database schema in a dedicated follow-up change.
4. Remove credential/logging issues, enforce JWT-only authentication, and correct CORS/configuration/dependencies.
5. Verify account, trade, role, and market-calendar behavior with an isolated test database.
6. Archive obsolete variants with attribution, then add screenshots and sanitized deployment/schema documentation where available.

This first cleanup change adds documentation and restores the owner-confirmed final capstone backend. It preserves the supplied source behavior; the outstanding security and runtime issues above have not been represented as fixed.
