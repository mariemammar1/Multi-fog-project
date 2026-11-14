# Multi-Fog EV - Intelligent Charging Recommendation Dashboard

A modern, responsive, and technically honest frontend dashboard for Electric Vehicle (EV) drivers, built for the project **"Collaborative Multi-Fog Architecture and DevOps for Intelligent Optimization of an Electric Vehicle Charging Network"**.

---

## 1. Quick Start

### Prerequisites
- Node.js (v18+ or v22+)
- Running Fog Services and Chronos-2 (Docker Compose):
  - Fog A: `http://localhost:8001`
  - Fog B: `http://localhost:8002`
  - Fog C: `http://localhost:8003`
  - Chronos-2 ML: `http://localhost:8000`

### Launch the Development Server
```bash
cd dashboard
npm install
npm run dev
```
The application will start at `http://localhost:5173/`.

### Production Build
```bash
npm run build
npm run preview
```

---

## 2. Core Driver Experience: "Which charging station should I choose right now?"

The dashboard answers the driver's primary question by combining:
1. **Physical local availability** from Fog SQLite databases (open piles, power ratings, connector types).
2. **Proximity & Travel Time** calculated from driver location coordinates.
3. **Territory-Level Context** from the shared Amazon Chronos-2 machine learning service (+1 hour ahead predicted regional occupancy).

### Multi-Objective Ranking Formula
Stations are ranked dynamically using the multi-objective scoring formula:

$$\text{Score} = w_{\text{travel}} \times \text{Norm}(\text{Travel Time}) + w_{\text{occupancy}} \times \text{Norm}(\text{Predicted Occupancy}) + w_{\text{wait}} \times \text{Norm}(\text{Waiting Time})$$

- **Travel Time Weight ($w_{\text{travel}}$):** Default $0.45$ (prioritizes short trips and low battery consumption).
- **Territory Occupancy Weight ($w_{\text{occupancy}}$):** Default $0.35$ (steers drivers away from saturating regional Fog territories).
- **Waiting Time Weight ($w_{\text{wait}}$):** Default $0.20$ (penalizes stations with few remaining open piles).

Drivers can customize weights and filter by:
- Connector capability (DC Fast Charging $>30\text{ kW}$ vs AC Standard $\le 22\text{ kW}$).
- Minimum power output (All, $\ge 50\text{ kW}$, $\ge 120\text{ kW}$ Ultra-Fast).
- Fog Territory (Fog A Central, Fog B Eastern, Fog C Western).
- Maximum driving radius ($5\text{ km}$, $10\text{ km}$, $25\text{ km}$, $50\text{ km}$).

---

## 3. Enhanced User Experience & Interactive Features

- **Active Destination & Route Tracer:** Selecting "Définir comme Cible" or "Choisir & Naviguer" sets the active destination, displays a persistent top banner pill, switches to the interactive map, and traces a live dashed route line with distance readouts.
- **Real GPS Geolocation:** Quick-detect button in the header requests real browser GPS coordinates with instant distance recalculation.
- **Toast Notifications:** Feedback alerts when stations are selected, preferences are reset, or live Fog telemetry is synchronized.
- **Departure Horizon Simulator:** In the Chronos-2 forecast section, users can simulate departure horizons (+1h, +2h, +3h) to inspect expected territory load trends.
- **Modern Light Theme:** Clean aesthetic with CartoDB Voyager basemap, white elevated cards, high-contrast typography, and territory color coding.

---

## 4. Data Truthfulness Matrix & Provenance

| Data Element | Source | Nature | Description & Limitations |
| :--- | :--- | :--- | :--- |
| **Station Coordinates & IDs** | SQLite (`stations` table) | **Real** | Exact WGS-84 coordinates for 1,635 stations across Shenzhen from the UrbanEV dataset. |
| **Charging Pile Telemetry** | SQLite (`piles` table) | **Real** | 22,138 charging piles with rated power (3.5 kW to 360 kW), AC/DC types, and reservation state. |
| **Fog Regional Capacities** | Fog Nodes (`GET /api/v1/piles/capacity`) | **Real / Live** | Real-time capacity aggregated by Fog territory (Fog A: 6,083 piles, Fog B: 7,403 piles, Fog C: 8,652 piles). |
| **Chronos-2 Forecasts** | Chronos-2 via Fog (`GET /api/v1/forecasts`) | **Real / Live ML** | Pretrained Amazon Chronos-2 zero-shot probabilistic model predicting aggregate occupied points (`busy`) 1 hour ahead ($q10, q50, q90$). |
| **Territory-Level Scope** | ML System Design | **Contextual** | **Chronos-2 predicts territory-level occupancy, NOT single-station occupancy.** The dashboard honestly presents this as regional context rather than fabricating fake station-level telemetry. |
| **Historical Observations** | UrbanEV CSVs (`ml-service/data/`) | **Empirical Research** | 4,345 hourly observations per Fog (Sept 2022 - Feb 2023) used for context and validation benchmarks. |
| **Driver Location** | Frontend State | **Selectable / GPS** | User can choose from preset Shenzhen metropolitan hubs (Nanshan, Futian, Bao'an, Luohu, Longgang) or use GPS. |
| **Estimated Waiting Time** | Derived Queue Model | **Simulated / Estimated** | Stations with $\ge 3$ open piles estimate 0 min wait. When all piles are in use, wait is estimated from average session duration and territory congestion. |

---

## 5. Chronos-2 Evaluation Benchmark

| Fog Node | Territory | Chronos-2 MAE | Baseline MAE | Performance Gain |
| :--- | :--- | ---:| ---:| :--- |
| **Fog A** | Central (Nanshan / Futian) | **32.36** | 34.54 | $+6.3\%$ error reduction |
| **Fog B** | Eastern (Luohu / Longgang) | **71.92** | 87.67 | $+17.9\%$ error reduction |
| **Fog C** | Western (Bao'an / Qianhai) | **68.76** | 68.67 | Baseline parity |

---

## 6. Strict Scope Restrictions & DevOps Compliance

- **Zero backend modification:** No changes to Fog-to-Fog cooperation protocols (`HELP_REQUEST`, `PROPOSAL`, `DECLINE`), reservation negotiation (`HOLD`, `CONFIRM`, `CANCEL`), Docker configurations, or Chronos ML weights.
- **Vite Reverse Proxy:** Securely routes `/fog-a`, `/fog-b`, `/fog-c`, and `/chronos` to ports 8001, 8002, 8003, and 8000 without requiring CORS changes on the FastAPI backend.
