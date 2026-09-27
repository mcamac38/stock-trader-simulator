# Stock Trading Simulator

A browser-based stock trading simulator built as a three-person, 15-week Arizona State University IT capstone. We built the application to let users manage simulated funds, buy and sell shares, and track their portfolios, with administrative tools for managing stocks and market schedules.

The project connects a JavaScript frontend to a Python Flask API and a PostgreSQL database across AWS Amplify, API Gateway, EC2, and Aurora.

**This is an academic simulation using virtual funds. It does not place real brokerage orders.**

## Features

| Area | What the application does |
| --- | --- |
| Accounts | Register, log in, and access user or administrator functionality |
| Simulated funds | Deposit and withdraw virtual cash and view account balances |
| Trading | Buy and sell shares, check holdings, and apply market-hours rules |
| Portfolio | View holdings, portfolio value, available cash, and total equity |
| Transactions | Review trade and cash-movement history with type and ticker filters |
| Stock management | Create and update stocks through administrative functionality |
| Market schedules | Configure market hours, weekend trading, and date-specific closures or special hours |
| Market overview | Display prices, share counts, calculated market capitalization, and charts |
| Price simulation | Apply simulated price updates with a 15-minute eligibility interval |

Charts use educational data: ticker history is generated from current prices, and portfolio history accumulates transaction movements. They are not a live market feed or a complete historical investment-performance calculation.

## Architecture

The capstone used a static frontend hosted on AWS Amplify, a Flask API running through Gunicorn on EC2, and an Aurora PostgreSQL database. API Gateway provided the HTTPS endpoint used by the browser.

| Component | Technology | Responsibility |
| --- | --- | --- |
| Frontend | HTML, CSS, JavaScript, Chart.js | Forms, navigation, market displays, portfolio charts, and API requests |
| Frontend hosting | AWS Amplify | Host the frontend and deploy updates from GitHub |
| API entry point | Amazon API Gateway | Receive HTTPS requests and forward them to the backend |
| Backend | Python, Flask, Gunicorn on Amazon EC2 | Process account, trading, portfolio, and administrative requests |
| Service management | systemd | Manage the backend process on EC2 |
| Database | Amazon Aurora PostgreSQL | Store users, balances, stocks, positions, transactions, and market configuration |

### Request flow

1. A user opens the frontend served by Amplify.
2. The browser sends an API request through the HTTPS API Gateway endpoint.
3. Flask processes the request on EC2, checks authentication or permissions where required, and reads or updates Aurora PostgreSQL.
4. The API returns JSON, and the frontend updates the page.

### Deployment workflow

GitHub primarily supported frontend deployments through Amplify. The Flask/Gunicorn backend was deployed separately on EC2.

The final capstone backend, retained separately as `SRE_Stock_Sim_Current`, has been restored as [`backend/app.py`](backend/app.py). The architecture above describes the capstone deployment; current AWS service availability has not been verified.

## Repository guide

| Path | Contents |
| --- | --- |
| [`frontend/Trading_System/index.html`](frontend/Trading_System/index.html) | Market overview and application entry page |
| [`frontend/Trading_System/pages/`](frontend/Trading_System/pages/) | Account, trading, portfolio, and administrative pages |
| [`frontend/Trading_System/javascript/api.js`](frontend/Trading_System/javascript/api.js) | Shared API client and browser token handling |
| [`frontend/Trading_System/css/styles.css`](frontend/Trading_System/css/styles.css) | Shared frontend styles |
| [`backend/app.py`](backend/app.py) | Final capstone Flask backend |
| [`backend/requirements.txt`](backend/requirements.txt) | Backend dependency list |
| [`backend/tests/test_health.py`](backend/tests/test_health.py) | Backend health-endpoint test |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Automated checks |
| [`docs/REPOSITORY_REVIEW.md`](docs/REPOSITORY_REVIEW.md) | Backend provenance, security findings, and remaining cleanup |
| [`docs/FILE_INVENTORY.md`](docs/FILE_INVENTORY.md) | Current application files and historical-file removal candidates |

Earlier snapshots and prototypes are still present pending cleanup. The file inventory identifies the current application versions.

## Authentication

Registration hashes passwords with Werkzeug before storing them in PostgreSQL. Login checks the password hash and issues an HS256 JWT with a one-hour lifetime. The frontend stores the token in `localStorage` and sends it using the `Authorization: Bearer` header. Backend routes retrieve user information from the database, and administrative routes check the user's role.

The retained code also contains a legacy username-token fallback and a default development signing secret. These require correction before redeployment. Additional findings are documented in the [repository review](docs/REPOSITORY_REVIEW.md).

## Setup status

This repository preserves the capstone application, but a fresh-clone, end-to-end setup has not yet been verified. The restored backend passes syntax checking.

Before running or redeploying it, the remaining setup work includes:

- Verify and supply the database schema and initialization process.
- Complete the dependency list, which currently omits PyJWT and Gunicorn.
- Configure database access, the JWT signing secret, and the allowed frontend origin.
- Review frontend API URLs in `api.js` and individual pages.
- Resolve the documented security and link issues and test the integrated application.

The backend reads these environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_HOST`, `DATABASE_PORT` | Database connection address |
| `DATABASE_NAME` | Database name |
| `DATABASE_USER`, `DATABASE_PASSWORD` | Database credentials |
| `JWT_SECRET` | Token-signing secret |
| `AMPLIFY_ORIGIN` | Frontend origin used for CORS configuration |
| `PORT` | Port used for direct Flask startup |

Keep credentials and deployment-specific secrets outside Git. Complete database bootstrap scripts and the deployed systemd/API Gateway configuration are not included.

## Related project

[`stock-trading-sre-platform`](https://github.com/mcamac38/stock-trading-sre-platform) is a separate follow-on project for reliability and operations practice. This repository covers the original ASU capstone and its Amplify, API Gateway, EC2, and Aurora architecture.
