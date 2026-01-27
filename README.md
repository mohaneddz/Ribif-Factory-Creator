<h1 style="font-family: Arial, sans-serif; font-size: 34px; color: #EAC360; display: flex; align-items: center; gap: 12px; border-bottom: 3px solid #EAC360; padding-bottom: 8px;">
  <img src="screenshots/logo.webp" alt="RIBIF 3D" style="height: 55px; width: 100px; object-fit: cover; border-radius: 8px;">
  RIBIF - Industrial Investment Platform
</h1>

RIBIF is an end-to-end industrial project intelligence platform that transforms technical machine/material documentation into a complete virtual factory decision package.  
The platform combines technical extraction, procurement intelligence, financial simulation, and operational visualization in one workflow.

---

## Global Objective

RIBIF is designed to support industrial companies from pre-engineing to investment decision by chaining **9 modules** into one coherent process.

Input:
- Technical files (`PDF`, `DOCX`) and structured payloads

Output:
- Structured technical requirements
- Supplier shortlists with contact and pricing evidence
- Negotiation traces (email + voice)
- Multi-year TCO model
- Business plan and pitch deck outputs
- 2D/3D layout artifacts
- HD walkthrough video
- Digital twin KPI views
- Technical catalog deliverables

---

## Status

Hackathon-demo-complete. Built end-to-end during EliteHack; most modules run through the full workflow, but polish is uneven across them — some pipelines are solid, others are rougher and less battle-tested. Treat this as a working prototype/demo rather than a production system.

---

## Tech Used

![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-06B6D4?style=for-the-badge&logo=tailwindcss)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)

Core stack:
- Backend: Python, Flask, OpenAI/GenAI integrations, Pandas, Pydantic
- Frontend: Next.js App Router, React, TypeScript, Tailwind, Three.js/R3F
- Data and storage: Supabase

---

## Workflow Orchestration

The main workflow engine is implemented in `frontend/src/app/workflow/[id]/page.tsx`.

Execution order in the current pipeline:
1. Module 1 - Specification extraction
2. Module 4 - Supplier sourcing
3. Module 6 - TCO modeling
4. Module 7 - Business plan and pitch deck
5. Module 9 - Technical catalog
6. Module 2 - 2D/3D layout
7. Module 3 - Video rendering
8. Module 8 - Digital twin view (UI, not a blocking backend step)

This ordering prioritizes financial and procurement decisions early, then generates layout and visual outputs after constraints are stabilized.

---

## Module 1 - Tech Sheets and Needs Extraction

<img src="screenshots/analysis.jpg" alt="Module 1 - Analysis" width="85%"/>

Business purpose:
- Ingest unstructured technical documents
- Extract machine/material specifications, capacities, utility constraints, and operational requirements
- Build normalized stage-based payloads for downstream modules

Implementation:
- Endpoint: `POST /api/module1/process`
- Status polling: `GET /api/module1/status`
- Result polling: `GET /api/module1/result`
- Route: `backend/routes/module1.py`
- Core logic: `backend/utils/module_1/`

Primary output:
- Structured extraction JSON (stages 1..6), including machine/equipment requirements

---

## Module 2 - Factory Layout (2D + 3D)

<img src="screenshots/2d.png" alt="Module 2 - 2D Layout" width="85%"/>
<br>
<img src="screenshots/3d.jpg" alt="Module 2 - 3D Layout" width="85%"/>

Business purpose:
- Convert technical extraction outputs into plant/workshop layout artifacts
- Generate 2D and 3D visualizations of zoning, flow, and equipment placement

Implementation:
- Endpoint: `POST /api/module2/layout`
- Route: `backend/routes/module2.py`
- Pipeline engine: `backend/utils/module_2/`

Primary output:
- 2D layout artifacts (DXF/PNG variants)
- 3D model artifacts (`GLB`-style workflow representation)

---

## Module 3 - HD Video Rendering

<img src="screenshots/video.jpg" alt="Module 3 - Video" width="85%"/>

Business purpose:
- Generate investor-ready short walkthrough videos from layout/visual context

Implementation:
- Endpoint: `POST /api/module3/video`
- Route: `backend/routes/module3.py`

Primary output:
- HD video artifact (`.mp4`) and downloadable URL

---

## Module 4 - Automated Supplier Sourcing

<img src="screenshots/suppliers.jpg" alt="Module 4 - Suppliers" width="85%"/>

Business purpose:
- Discover supplier candidates globally
- Aggregate signals such as pricing, lead-time, and contact evidence
- Rank options per machine family

Implementation:
- Endpoint: `POST /api/module4/enrich`
- Route: `backend/routes/module4.py`
- Core logic: `backend/utils/module_4/`
- Search providers/aggregation: `backend/utils/web_search/`

Primary output:
- Enriched supplier lists with relevance and sourcing traces

---

## Module 5 - AI Negotiation (Email + Voice)

<img src="screenshots/email.jpg" alt="Module 5 - Email Negotiation" width="85%"/>
<br>
<img src="screenshots/call.jpg" alt="Module 5 - Voice Negotiation" width="85%"/>

Business purpose:
- Support iterative negotiation with suppliers through text and voice channels
- Produce negotiation history and best-offer summaries

Implementation:
- Endpoints:
  - `POST /api/module5/text/negotiation`
  - `POST /api/module5/voice/negotiation`
  - `POST /api/module5/voice/summary`
- Route: `backend/routes/module_5.py`
- Negotiation core: `backend/utils/module_5/`
- Email integration: `backend/routes/email_service.py`

Frontend voice UI:
- `frontend/src/app/voice-call/page.tsx`

Primary output:
- Negotiation rounds, transcript data, and negotiated pricing traces

---

## Module 6 - TCO (Total Cost of Ownership)

<img src="screenshots/tco.jpg" alt="Module 6 - TCO" width="85%"/>

Business purpose:
- Estimate realistic industrial ownership cost over multi-year horizons
- Include acquisition, installation, operations, maintenance, and yearly projections

Implementation:
- Endpoints:
  - `POST /api/module6/tco-from-sourcing`
  - `POST /api/module6/tco`
- Route: `backend/routes/module6.py`
- Core model: `backend/utils/module_6/core.py`

Primary output:
- Machine/product/raw-material TCO breakdowns and annual projection

---

## Module 7 - Automatic Business Plan

<img src="screenshots/business.jpg" alt="Module 7 - Business Plan" width="85%"/>

Business purpose:
- Transform technical and financial outputs into investor-facing business material
- Generate 5-year planning artifacts and pitch-ready content

Implementation:
- Endpoints:
  - `POST /api/module7/business-plan`
  - `POST /api/module7/pitch-deck`
- Route: `backend/routes/module7.py`
- Generators:
  - `backend/utils/module_7/business_plan.py`
  - `backend/utils/module_7/pitch_deck.py`

Primary output:
- Business plan assets and pitch deck outputs

---

## Module 8 - Digital Twin and Digital Brain

<img src="screenshots/twin.jpg" alt="Module 8 - Digital Twin" width="85%"/>

Business purpose:
- Provide an operational digital twin with KPI visualization and monitoring
- Expose throughput/availability/quality-style views for decision support

Implementation in this repo:
- Page route: `frontend/src/app/twin/page.tsx`
- Main view: `frontend/src/sections/DigitalTwinView.tsx`

Primary output:
- Live/interactive KPI and factory twin views in the frontend

---

## Module 9 - Automatic Technical Catalog

<img src="screenshots/catalogue.jpg" alt="Module 9 - Catalog" width="85%"/>

Business purpose:
- Produce reusable technical documentation and catalog output for equipment/process context

Implementation:
- Endpoint: `POST /api/module9/catalog`
- Route: `backend/routes/module9.py`
- Core generator: `backend/utils/module_9/core.py`

Primary output:
- Catalog payload and PDF-ready artifact links

---

## Supporting Views

### Home
<img src="screenshots/home.jpg" alt="Home" width="85%"/>

### Workflow Loading
<img src="screenshots/loading.jpg" alt="Loading" width="85%"/>

### PDF Preview
<img src="screenshots/pdf.jpg" alt="PDF Preview" width="85%"/>

---

## Repository Structure

```text
ribif/
|- backend/
|  |- app.py
|  |- config.py
|  |- requirements.txt
|  |- routes/
|  |  |- module1.py
|  |  |- module2.py
|  |  |- module3.py
|  |  |- module4.py
|  |  |- module_5.py
|  |  |- module6.py
|  |  |- module7.py
|  |  |- module9.py
|  |- utils/
|  |  |- module_1/
|  |  |- module_2/
|  |  |- module_4/
|  |  |- module_5/
|  |  |- module_6/
|  |  |- module_7/
|  |  |- module_9/
|  |  |- web_search/
|- frontend/
|  |- src/app/
|  |- src/sections/
|  |- src/lib/
|  |- supabase/
```

---

## Environment Variables

Backend (`backend/.env`):
- `GOOGLE_API_KEY`
- `GEMINI_MODEL`
- `IMAGE_MODEL`
- `VIDEO_MODEL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SERPER_API_KEY`
- `BING_API_KEY`
- `WEB_SEARCH_ENABLED`
- `PREFER_WEB_DATA`
- `CORS_ORIGINS`
- `BACKEND_BASE_URL`

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_VAPI_PUBLIC_KEY`

---

## API Surface (Core)

- `POST /api/module1/process`
- `GET /api/module1/status`
- `GET /api/module1/result`
- `POST /api/module2/layout`
- `POST /api/module3/video`
- `POST /api/module4/enrich`
- `POST /api/module5/text/negotiation`
- `POST /api/module5/voice/negotiation`
- `POST /api/module5/voice/summary`
- `POST /api/module6/tco-from-sourcing`
- `POST /api/module6/tco`
- `POST /api/module7/business-plan`
- `POST /api/module7/pitch-deck`
- `POST /api/module9/catalog`

Supporting:
- `GET /health`
- `GET /health/ready`
- `GET /health/live`
- `GET /health/metrics`
- `POST /api/validate-pdf`
- `POST /api/extract-text`
- `POST /api/email/send`
- `POST /api/email/poll`

---

## Quick Start

Prerequisites:
- Python 3.10+
- Node.js 20+
- `pnpm`

Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Frontend:
```bash
cd frontend
pnpm install
pnpm dev
```

Default URLs:
- Backend: `http://localhost:5000`
- Frontend: `http://localhost:3000`

---

## Development Verification

Frontend checks:
```bash
cd frontend
pnpm lint
pnpm test
```

Backend checks (examples from repository):
```bash
cd backend
python test_imports.py
python test_module4_budget_enforcement.py
python test_module1_refactor.py
```
