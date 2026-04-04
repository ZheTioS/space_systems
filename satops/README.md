# SatOps Dashboard

A lightweight web-based ground segment workbench for satellite communications. Connects to an RTL-SDR to track satellite passes, visualize RF activity, compute link budgets, and log observations in real time.

## Features

- **SDR Integration** — connect to RTL-SDR via SoapySDR, configure frequency/gain/sample rate, view live spectrum and waterfall displays
- **Pass Tracking** — predict satellite passes using TLE data from CelesTrak, compute azimuth/elevation/range in real time via Skyfield
- **Doppler Estimation** — calculate and display predicted Doppler shift over each pass
- **Link Budget** — real-time FSPL, received power, noise power, and SNR computation that updates dynamically with satellite range
- **Observation Logging** — record pass sessions with signal metrics and notes
- **Mission Control UI** — dark-themed dashboard with live WebSocket updates

## Architecture

```
satops/
  backend/                Python/FastAPI (uv)
    satops_backend/
      api/                REST + WebSocket routes
      services/           Business logic (SDR, tracking, link budget, observations)
      config.py           Pydantic Settings — all config via SATOPS_ env vars
      db.py               SQLite via aiosqlite
      schemas.py          Pydantic models
      main.py             App entry point
  frontend/               React/TypeScript (Bun + Vite)
    src/
      components/         Panel-based UI (TopBar, PassPanel, SpectrumPanel, LinkBudgetPanel, PassHistory)
      store/              Zustand state management
      hooks/              WebSocket connection hook
      services/           REST API client
      config.ts           Frontend config via VITE_ env vars
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/)
- RTL-SDR dongle + SoapySDR (optional — runs in synthetic data mode without hardware)

### Backend

```bash
cd satops/backend
uv sync
uv run uvicorn satops_backend.main:app --reload
```

The API starts at `http://127.0.0.1:8000`. On first run it:
- Creates a SQLite database with NOAA 15/18/19 satellite entries
- Fetches TLE data from CelesTrak
- Starts the SDR in synthetic mode (if no hardware detected)

### Frontend

```bash
cd satops/frontend
bun install
bun dev
```

Opens at `http://localhost:5173`. The Vite dev server proxies `/api` and `/ws` to the backend.

## Configuration

All backend settings are configurable via environment variables with the `SATOPS_` prefix, or via a `.env` file. See [`backend/.env.example`](backend/.env.example) for the full list.

Frontend settings use `VITE_` prefixed variables. See [`frontend/.env.example`](frontend/.env.example).

Key settings:

| Variable | Default | Description |
|---|---|---|
| `SATOPS_SDR_FREQUENCY_HZ` | `137100000` | SDR center frequency (Hz) |
| `SATOPS_SDR_GAIN` | `40.0` | SDR gain (dB) |
| `SATOPS_OBSERVER_LAT` | `52.52` | Ground station latitude |
| `SATOPS_OBSERVER_LON` | `13.405` | Ground station longitude |
| `SATOPS_MIN_PASS_ELEVATION_DEG` | `5.0` | Minimum elevation for pass prediction |
| `SATOPS_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |

## Target Satellites

Pre-configured for NOAA weather satellites at ~137 MHz:

| Satellite | NORAD ID | Frequency |
|---|---|---|
| NOAA 15 | 25338 | 137.620 MHz |
| NOAA 18 | 28654 | 137.9125 MHz |
| NOAA 19 | 33591 | 137.100 MHz |

## API

- `GET /api/health` — health check + SDR status
- `GET /api/tracking/satellites` — list configured satellites
- `GET /api/tracking/position/{norad_id}` — current satellite position
- `GET /api/tracking/passes/{norad_id}` — upcoming passes
- `POST /api/tracking/tle/refresh` — force TLE refresh
- `GET /api/sdr/status` — SDR connection status
- `POST /api/sdr/connect` / `disconnect` — SDR control
- `POST /api/link-budget/compute` — compute link budget
- `GET /api/observations/` — observation history
- `WS /ws` — multiplexed WebSocket for live tracking, spectrum, and link budget updates

## Development

```bash
# Lint backend
cd satops/backend && uv run ruff check .

# Type-check frontend
cd satops/frontend && bun run tsc --noEmit

# Run pre-commit hooks
cd satops/backend && uv run pre-commit run --all-files
```
