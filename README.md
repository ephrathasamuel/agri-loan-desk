# Agri-Loan Climate Risk Desk

A full-stack tool for **agricultural loan officers**. The officer draws a smallholder farmer's field on a satellite map and enters the crop, planting date and requested loan. The desk then replays that crop season in every year since 1984, using the real daily weather for that exact field, and returns three things:

1. **Climate risk for the field:** season rainfall for every year, how often the season was dry, and the yield lost to water stress in each year.
2. **A loan structure that fits the farm:** repayment dates after the expected harvest, and the largest loan the harvest could still repay in a 1-in-5 bad year.
3. **A priced drought insurance option:** a weather-index policy (trigger, exit, premium) designed and back-tested on the same 42 seasons. It shows the years it would have paid, and also the bad years it would have missed.

An AI briefing note (Claude) can then explain the result to the officer in English or Amharic, using only the computed numbers.

It is built with **Next.js (React) + FastAPI (Python) + PostgreSQL/SQLite**, with sign-in for loan officers, saved assessment history, GIS field boundaries, Docker, and CI. It is a working prototype, not a credit model trained on repayment data (see [Limitations](#limitations)).

<p>
  <img src="docs/screenshot-result.png" alt="Assessment result: climate risk, loan structure, insurance backtest and field map for a wheat field near Bishoftu" width="70%" />
  <img src="docs/screenshot-mobile.png" alt="The same result on a phone" width="22%" />
</p>
<p>
  <img src="docs/screenshot-new.png" alt="New assessment: drawing the field boundary on the satellite map" width="49%" />
  <img src="docs/screenshot-list.png" alt="Saved assessments" width="49%" />
</p>

---

## Quick start (Docker)

```bash
cp .env.example .env     # fill in SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, POSTGRES_PASSWORD
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:3000 | The desk. Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` |
| http://localhost:8000/docs | Interactive API docs (OpenAPI / Swagger) |

Compose runs three Linux containers: **PostgreSQL 17**, the **FastAPI** risk engine and the **Next.js** server. The first admin account is created from the environment on first start; add loan officers from the **Officers** page.

## Local run (no Docker)

```bash
# API: Python 3.13, SQLite by default
cd api
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy ..\.env.example .env              # macOS/Linux: cp ../.env.example .env, then fill it in
uvicorn app.main:app --port 8000

# Web: Node 24, in a second terminal
cd web
npm install
npm run dev                            # http://localhost:3000 (API_URL defaults to http://127.0.0.1:8000)
```

The weather data (NASA POWER) is free and needs no key. `ANTHROPIC_API_KEY` is optional: without it everything works except the AI briefing note, and the page says why.

---

## What the officer sees

- **Field and data:** the field on satellite imagery, plus the NASA POWER grid cells its weather history came from.
- **Headline numbers:** share of bad seasons, maximum loan in a 1-in-5 bad year against the amount requested, drought cover premium, repayment date.
- **Loan structure:** a timeline (loan paid out, planting, expected harvest, repayment due), interest, harvest value in a bad and a median year, and a verdict: *Within capacity*, *Repayable in a normal year only* or *Above capacity*.
- **Climate risk:** charts of season rainfall and estimated yield loss for every season since 1984, with dry seasons and bad seasons marked.
- **Drought insurance:** trigger and exit in mm, premium, maximum payout per hectare, a back-test chart, and a **basis risk** panel. It lists bad seasons the index would not have paid for, and payouts in years with little loss.
- **AI briefing note:** Claude explains the case in English or Amharic. It is told not to approve or reject the loan, and to separate measured history from assumptions.
- **Assumptions used:** every assumption behind the money figures, labelled as an assumption or as an officer override.
- **History:** every assessment is saved with its full result. Officers see their own; admins see all.

---

## How the risk is calculated

The engine is in [`api/app/risk/`](api/app/risk). Every agronomic value carries the number of the FAO table it comes from.

**1. Weather history (NASA POWER).** The API downloads daily rainfall, temperature, humidity, wind and solar radiation from the [NASA POWER](https://power.larc.nasa.gov/) daily API for 1984 to the last complete year. That is 42 seasons, starting in 1984 because POWER's solar radiation starts mid-1983. Rainfall is POWER's `PRECTOTCORR` (MERRA-2 based). POWER serves data on a 0.5° × 0.625° grid, so each grid cell is downloaded once and cached in the database. **If the drawn field touches more than one grid cell, the daily series are averaged across them.**

> CHIRPS (0.05°) would give finer rainfall. It needs bulk raster downloads rather than a point API, so it is listed as the next step under [Limitations](#limitations).

**2. Reference evapotranspiration.** ET₀ is computed for every day with the **FAO-56 Penman-Monteith** equation ([`et0.py`](api/app/risk/et0.py)), and is tested against FAO-56 Example 18.

**3. The season, replayed for each year** ([`season.py`](api/app/risk/season.py)):
- The crop coefficient Kc and rooting depth follow the FAO-56 crop curve from the planting date (Tables 11, 12, 22).
- A daily root-zone **water balance** (FAO-56 eq. 85) with effective rain. The crop is stressed (Ks < 1, eq. 84) once it has used its readily available water.
- 30 days of bare-soil spin-up before planting, so each year starts from that year's rains.
- **Yield loss from water stress** uses the FAO-33 yield response: `1 − Ya/Ym = Ky × (1 − ETa/ETm)`.

**4. Risk summary.** A *dry season* has rainfall below 75% of the median. A *bad season* loses at least 20% of its yield. The climate risk rating is Low (under 10% bad seasons), Medium (under 25%) or High.

**5. Loan structure** ([`engine.py`](api/app/risk/engine.py)):
- **Dates.** The loan is paid out 14 days before the next planting date and falls due 30 days after the expected harvest. Harvest is planting plus the FAO-56 season length.
- **Harvest value in a bad year.** Area × typical yield × the 20th-percentile relative yield from the history × price.
- **Maximum loan.** The share of the harvest value set aside for repayment, divided by (1 + interest for the loan's term).

**6. Weather-index insurance** ([`insurance.py`](api/app/risk/insurance.py)):
- **Index.** Rainfall from planting to the end of mid-season, the water-sensitive part of the season.
- **Trigger and exit.** The 20th and 5th percentiles of the historical index. Officers can change both.
- **Payout.** Rises in a straight line from 0 at the trigger to the full sum insured at the exit. The sum insured is the loan amount.
- **Premium.** The average payout over all 42 years (the "burning cost") plus a 25% loading.
- **Basis risk is reported both ways.** Bad seasons with no payout, and payouts with little loss.

**7. AI briefing note** ([`summary.py`](api/app/summary.py)). The saved result is sent to `claude-opus-5-5` through the Anthropic Python SDK. The instructions say to use only the numbers given, never to decide the loan, and to name the assumptions that matter. If the model declines, the API retries on Anthropic's recommended fallback model. If it still declines, the page says so.

### Assumptions (not facts)

All money assumptions sit in one file, [`api/app/risk/assumptions.py`](api/app/risk/assumptions.py), and every result page lists the ones it used:

| Assumption | Default | Note |
|---|---|---|
| Typical yield (t/ha) | wheat 3.0, teff 1.9, maize 4.2, sorghum 2.9, barley 2.5 | Rounded from CSA national averages; officers can override per assessment |
| Farm-gate price (ETB/quintal) | wheat 6,000, teff 12,000, maize 4,000, sorghum 5,000, barley 6,000 | Placeholders; officers should enter the current local price |
| Share of harvest value for repayment | 40% | |
| Interest rate | 18% a year, flat | |
| Disbursement / grace | 14 days before planting / 30 days after harvest | |
| Insurance loading | 25% | |

Teff and barley have no seasonal Ky in FAO-33, so Ky = 1.0 is assumed. Teff uses small-grain FAO-56 values. Both are shown as notes in the app.

---

## Architecture

```mermaid
flowchart LR
  B[Browser<br/>React, Leaflet, Recharts] -->|forms, server actions| W[Next.js 16 server<br/>App Router, httpOnly session cookie]
  W -->|REST + Bearer token| A[FastAPI risk engine<br/>typed Pydantic models, OpenAPI]
  A --> D[(PostgreSQL / SQLite<br/>SQLAlchemy 2)]
  A -->|daily history, cached per grid cell| N[NASA POWER API]
  A -->|briefing note, optional| C[Claude API]
```

- **The browser never calls the API directly.** Pages and server actions call it from the Next.js server, with the officer's token kept in an httpOnly cookie.
- **FastAPI** owns everything else: sign-in, roles, validation, the risk engine and the database. Passwords are scrypt hashes. Session tokens are HMAC-signed and stop working when the password changes. Five failed sign-ins lock the account for 10 minutes.
- **Typed models.** Every request and response is a typed Pydantic model, so the OpenAPI docs at `/docs` are complete.
- **GIS.** The field boundary is stored as a GeoJSON Polygon. Its area is calculated on the server with a geodesic (spherical-excess) formula; the browser shows the same calculation live while drawing.
- **Databases.** Docker Compose uses PostgreSQL. Local runs and tests use SQLite unless `DATABASE_URL` / `TEST_DATABASE_URL` say otherwise.

| Path | What it does |
|---|---|
| `api/app/risk/` | Pure-Python risk engine: crops, ET₀, season simulation, insurance, loan, geometry |
| `api/app/main.py` | FastAPI routes: auth, users, reference data, assessments, AI note, health |
| `api/app/db.py` | SQLAlchemy models: users, assessments (with GeoJSON), climate cache |
| `web/app/` | Next.js pages: sign-in, assessment list, new assessment, results, officers |
| `web/components/` | Field drawing map, result map, charts |
| `web/e2e/` | Playwright end-to-end tests |
| `.github/workflows/ci.yml` | CI: API tests on SQLite and PostgreSQL, web lint, build and end-to-end tests, Docker image build |

---

## Tests

```bash
cd api && python -m pytest          # risk maths, climate client, geometry, API, AI note (no network)
cd web && npm run build && npm run test:e2e   # starts the API and web app; needs internet for NASA POWER
```

- **API tests (pytest), 62 in total:**
  - FAO-56 worked examples: saturation vapour pressure, Example 8 (Ra), Example 18 (daily ET₀).
  - Water balance and FAO-33 yield response.
  - Percentile, payout and premium maths, and basis-risk flags.
  - Loan dates and capacity, and polygon area.
  - The NASA POWER client against faked responses and failures.
  - The AI note with a faked client.
  - The HTTP API: sign-in, lockout, roles, validation, officer isolation, and password change signing out old sessions.
- **End-to-end tests (Playwright), 5 in total:**
  - Pages are blocked until you sign in, and a wrong password is refused.
  - **Draw a real field near Bishoftu, assess it against live NASA POWER data,** and find it in the history.
  - An admin adds an officer, who sees only their own assessments.
  - The results page has no sideways scroll on a phone.
- **CI** runs the API tests on SQLite and on a PostgreSQL service, then lint, build and the end-to-end tests, and builds both Docker images on Linux.

---

## Deploy (free tiers)

| Part | Host | Notes |
|---|---|---|
| Database | **Neon** or **Supabase** (PostgreSQL) | Neon: free with no expiry, copy the connection string. Supabase: use the **Session pooler** string (port 5432, IPv4) |
| Risk API | **Render** (Docker, from `render.yaml`) | Free plan sleeps after 15 minutes idle |
| Web app | **Vercel** (Next.js) | Root directory `web` |

1. **Database:** on **Neon**, create a project (region near the API, e.g. Frankfurt) and copy the connection string from *Connect*. Or on **Supabase**, *Connect → Session pooler* and copy the URI, replacing `[YOUR-PASSWORD]`. The app accepts either address as shown (`postgresql://…`, including `?sslmode=require`); tables are created on first start.
2. **Render:** *New → Blueprint*, pick this repository. Render reads `render.yaml`, generates `SECRET_KEY`, and asks for `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` and the optional `ANTHROPIC_API_KEY`. When it is live, open `https://<service>.onrender.com/health`.
3. **Vercel:** *Add New → Project*, import this repository, set **Root Directory** to `web`, and add the environment variable `API_URL` = the Render address (no trailing slash). Deploy.
4. **Keep the API awake (optional):** in GitHub, *Settings → Secrets and variables → Actions → Variables*, add `API_HEALTH_URL` = `https://<service>.onrender.com/health`. The `keep-warm` workflow then pings it every 14 minutes.

The browser never calls the API: Next.js server code calls it with `API_URL`, so no CORS setup is needed.

---

## Limitations

- **No repayment data.** The desk estimates *climate* risk from weather and an agronomic model. It does not know the farmer's credit history, other income or management, and the money figures depend on the assumptions above. It supports an officer's judgement; it does not replace a credit model.
- **Coarse rainfall.** NASA POWER rainfall is a ~50 km grid average, which smooths local storms and dry spells. CHIRPS or station data would sharpen field-level risk.
- **Simplified agronomy.** A single-layer bucket model with fixed soil and crop values, no fertility, pests or late-season heat stress, and an assumed soil state before planting. Teff and barley Ky values are assumptions.
- **Insurance design is illustrative.** Linear payout on one cumulative rainfall index, priced on burning cost. A real product would use dekadal (10-day) phases, a reinsurer's loading and regulatory approval.
- **Future seasons are assumed to look like the past 42.** No climate-change trend is applied.
