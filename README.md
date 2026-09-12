# fluxyz

A commodity-market observatory: gold (GLD), oil (USO), coal mining equity (BTU),
rolling correlations, astronomical proximity, geomagnetic activity, and solar
X-ray activity. Observations are not causal claims or investment advice.

## Architecture

React + TypeScript + Vite frontend on Vercel → FastAPI API and ingestion worker
on Railway → open-source StarRocks (`starrocks/allin1-ubuntu:3.5.21`) on Railway.

The API uses the MySQL protocol to query StarRocks. Only the API is public;
database ports stay on the private network. One API process owns ingestion.

## Development

Requires Node 22.12+ (Node 24 supported), Python 3.10+ (production: 3.12) and Docker.

```sh
npm ci
python3 -m venv .venv
.venv/bin/pip install -e './backend[dev]'
# Set variables from .env.example in your shell; do not commit .env files.
.venv/bin/uvicorn fluxyz.main:app --port 8000
npm run dev
```

## Checks

```sh
npm run lint
npm run typecheck
npm run build
cd backend
../.venv/bin/ruff check .
../.venv/bin/mypy fluxyz
../.venv/bin/pytest
```

## Data policy

No simulated production data. If a source fails, show the last successful
reading with its timestamp and an explicit source error.

- Twelve Data: live market prices for GLD, USO and BTU, not physical spot prices.
- EIA: separate official coal reference; never plotted as live BTU.
- NOAA SWPC: public Kp and solar X-ray readings.
- Astronomical dates: calculated locally.
- Gemini Flash: commentary and chat grounded in stored observations.

## Credentials

All provider credentials belong in Railway's service variable manager. Vercel
receives only the public API URL (`VITE_API_URL`); no provider keys.
Rotate at Twelve Data's API dashboard, EIA's API registration account, Google AI
Studio, Vercel account token settings, and Railway account token settings, then
replace the corresponding deployment variables and redeploy. Revoke old keys.

Deployment instructions, measured source cadence, and observed-data limitations
will be updated as each service is verified.
