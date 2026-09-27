# Application file inventory

Reviewed all 32 files tracked at baseline commit `a3573464dfc9baf28c0e3cbd038bba97a4826d49`, together with the owner-confirmed final backend restored on this branch.

Method: inspect local page links, script tags, JavaScript imports and redirect targets, Python imports, API routes, CSS references, test imports, and CI configuration. Trace frontend navigation from `frontend/Trading_System/index.html`. Check candidate filenames for incoming references across the tracked source/configuration files. Documentation added by this review is listed separately below.

**Result: 15 frontend files participate in the current navigation/dependency structure, one backend is the owner-confirmed final application, four files support development, and 12 files are unreferenced historical/prototype candidates.** “Used” means referenced by this source structure, not independently verified against a running Amplify or EC2 deployment. A static file can remain directly accessible at its URL even if nothing links to it. The repository contains no Amplify build specification or EC2 service unit to establish exact deployed artifact selection.

## Keep: frontend application

Paths in this table are relative to `frontend/Trading_System/`.

| File | Evidence / purpose |
| --- | --- |
| `index.html` | Home/market entry page; linked throughout navigation |
| `css/styles.css` | Shared stylesheet referenced by the HTML pages |
| `javascript/api.js` | Shared module imported by current account, trading, portfolio, and admin pages |
| `pages/login.html` | Login destination; imports `loginUser`; redirects by database role |
| `pages/register.html` | Linked from login; imports `registerUser` |
| `pages/portfolio.html` | Default login destination and navigation target; imports `getPortfolio` and `getPortfolioHistory`; loads Chart.js |
| `pages/buy.html` | Navigation target; imports `placeOrder` and ticker history; contains chart implementation |
| `pages/sell.html` | Navigation target; imports `sellOrder` and ticker history; fetches user holdings for its dropdown |
| `pages/transactions.html` | Navigation target; uses the current transaction API helper |
| `pages/deposit.html` | Navigation target; imports `deposit` and cash helpers |
| `pages/withdraw.html` | Navigation target; imports `withdraw` and cash helpers |
| `pages/Admin-Dashboard.html` | Explicit admin destination in `login.html`; links to admin tools |
| `pages/admin-create-stock.html` | Navigation/dashboard target; uses the admin stock API |
| `pages/admin-market-hours.html` | Navigation/dashboard target; uses the market-hours API |
| `pages/admin-market-schedule.html` | Navigation/dashboard target; uses the market-schedule API |

These are the correct files to keep as the current frontend, rather than replacing them with numbered/backup variants or the older individual attachments. Most page behavior is inline JavaScript inside the HTML files, which explains why the separate teammate JavaScript snippets are not required to load those pages.

## Keep: backend and project support

| Repository path | Classification and evidence |
| --- | --- |
| `backend/app.py` | Canonical application path on this branch: restored from `SRE_Stock_Sim_Current`, explicitly identified by the project lead as the final capstone backend. Imports libraries, not the other local backend files. |
| `backend/requirements.txt` | Used by the backend CI install step. Keep and correct its missing runtime dependencies. |
| `backend/tests/test_health.py` | Imports `app` and tests `/health`; development support, not a second application. |
| `.github/workflows/ci.yml` | Backend quality/test steps and frontend link checks. GitHub Actions consumes it. |
| `.gitignore` | Git hygiene configuration. Keep and correct malformed patterns. |

The actual historical Gunicorn module name is not established by a committed service unit. Restoring the final source under `backend/app.py` makes it match the repository's existing application/test convention without asserting the original EC2 filename.

## Archive candidates: no incoming source references found

These are variants or standalone snippets, not necessarily byte-identical duplicates. No other tracked baseline file references these filenames. The selected backend does not import the Python candidates, and no frontend page loads the JavaScript candidates.

| Repository path | Reason |
| --- | --- |
| `backend/app.txt` | Earlier 510-line application snapshot stored as text; not imported or executed by current configuration |
| `backend/app1.0.py` | Earlier 295-line application variant; superseded by the confirmed final backend |
| `backend/app2.0.py` | Earlier 758-line application variant; superseded by the confirmed final backend |
| `backend/Kaylas_Code_Random.py` | Standalone in-memory price/cash prototype plus integration notes; creates its own Flask app and is not imported by the final backend |
| `backend/market hour change .py` | Standalone market-hours helper snippet; final backend defines its own helper |
| `frontend/Trading_System/javascript/Kelcies_Code_Portfolio.js` | Unloaded prototype; references older `/portfolio/holdings` endpoint |
| `frontend/Trading_System/javascript/Kelcies_Code_Transactions.js` | Unloaded prototype; references older `/portfolio/transactions` endpoint |
| `frontend/Trading_System/pages/portfolio1.0.html` | No incoming page links; imports `getHoldings`, which current `api.js` does not export |
| `frontend/Trading_System/pages/portfolio2.0.html` | No incoming page links; older chart variant with an HTTP `cdn.jsdeliver.net` script URL |
| `frontend/Trading_System/pages/portfolio_woChart.html` | No incoming page links; earlier portfolio without the current chart |
| `frontend/Trading_System/pages/sell(1).html` | No incoming page links; alternate sell implementation |
| `frontend/Trading_System/pages/sell_backup.html` | No incoming page links; backup sell implementation |

Recommended follow-up: remove these from active application directories in a dedicated cleanup commit, retaining Git history and team attribution. If an explicit archive is preferred, keep it outside the frontend hosting root and verify Amplify's artifact settings. No candidates have been deleted or relocated in this review branch.

## Issues revealed by tracing references

- `index.html:152` imports `../javascript/api.js`, while the module is actually at `./javascript/api.js` relative to that page. This is a broken source-relative import under the checked-in layout; deployment rewrites were not inspected.
- `Admin-Dashboard.html` links to lowercase `admin-dashboard.html`, which does not exist with that exact case. Login correctly points to `Admin-Dashboard.html`.
- Cancel links in `admin-market-hours.html` and `admin-create-stock.html` point to `./index.html`, resolving to nonexistent `pages/index.html`. The home file is one directory above.
- Several pages reference favicon, Apple-touch-icon, and social-card files in an `images` directory that is absent from the repository.
- `api.js` contains a `logout()` helper, but the current pages' Logout links navigate directly to login without invoking it. Navigation alone does not clear the stored token.
- The root-page authentication fallback in `api.js` points to `/login.html`, while the repository's login page is `/pages/login.html`. Relative redirects in this module resolve against the document URL, not the module directory.

These source-level findings are recorded for a separate behavior/link cleanup. The frontend has not been changed in this branch.

## New documentation

`README.md` describes the capstone, architecture, features, team-lead role, and project boundaries. `docs/REPOSITORY_REVIEW.md` records backend provenance and security/hygiene findings. This `docs/FILE_INVENTORY.md` records the file-selection decision. These documentation files are useful portfolio material, not runtime dependencies.
