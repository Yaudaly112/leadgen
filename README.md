# LeadGen AI — Website Outreach Agent

AI-powered lead generation system that discovers local businesses without websites, generates demo sites, and sends personalized outreach via email and phone.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Dashboard                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Campaigns │  │  Leads   │  │Approval  │  │ Settings │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Pipeline                           │  │
│  │  Discovery → Enrichment → Demo Generation → Outreach │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Places  │  │   LLM    │  │  Email   │  │  Phone   │   │
│  │   API    │  │ (OpenAI) │  │(SendGrid)│  │ (Twilio) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   PostgreSQL      Redis        Generated
   (Leads)        (Tasks)     Demo Sites
```

## Pipeline Flow

1. **Discover** — Find businesses via Google Places API that lack websites
2. **Enrich** — Generate AI descriptions and business content via OpenAI
3. **Demo** — Build a one-page demo website for each lead
4. **Outreach** — Send personalized cold emails (with human approval)
5. **Follow-up** — Automated follow-up sequences for non-responders
6. **Convert** — Track interested leads and hand off to sales

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Celery
- **Frontend:** Next.js, React, Tailwind CSS
- **Database:** PostgreSQL + Redis
- **APIs:** Google Places, OpenAI, SendGrid, Twilio

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### 1. Clone and install

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Configure environment

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start services

```bash
# PostgreSQL and Redis (if not running)
# Or use Docker Compose:
docker-compose up -d postgres redis

# Start the backend
cd backend
uvicorn app.main:app --reload --port 8000

# Start the Celery worker
celery -A app.tasks worker --loglevel=info

# Start the frontend
cd frontend
npm run dev
```

### 4. Open the dashboard

Navigate to [http://localhost:3000](http://localhost:3000)

## API Endpoints

### Campaigns
- `POST /api/campaigns` — Create a campaign
- `GET /api/campaigns` — List campaigns
- `GET /api/campaigns/:id` — Get campaign details

### Leads
- `GET /api/leads` — List leads (filterable)
- `GET /api/leads/:id` — Get lead details
- `PATCH /api/leads/:id` — Update a lead

### Pipeline Actions
- `POST /api/discover/:campaign_id` — Run discovery
- `POST /api/enrich/:lead_id` — Enrich a single lead
- `POST /api/demo/:lead_id` — Generate demo site
- `POST /api/outreach/cold-email/:lead_id` — Send cold email

### Background Tasks
- `POST /api/tasks/discover` — Queue discovery
- `POST /api/tasks/enrich-batch/:campaign_id` — Batch enrich
- `POST /api/tasks/generate-demos-batch/:campaign_id` — Batch generate demos
- `GET /api/tasks/status/:task_id` — Check task status

### Approval
- `GET /api/outreach/pending` — List pending emails
- `POST /api/outreach/approve/:log_id` — Approve and send

### Stats
- `GET /api/stats/dashboard` — Dashboard overview
- `GET /api/stats/campaign/:id` — Campaign stats

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── pipeline.py          # Main agent orchestration
│   │   ├── services/
│   │   │   ├── places.py            # Google Places API client
│   │   │   ├── llm.py               # OpenAI prompts & generation
│   │   │   ├── demo_generator.py    # Demo site builder
│   │   │   ├── email_sender.py      # SendGrid integration
│   │   │   └── phone.py             # Twilio phone/SMS
│   │   ├── templates/
│   │   │   └── demo_page.html       # Demo site HTML template
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── main.py                  # FastAPI app
│   │   ├── tasks.py                 # Celery background tasks
│   │   └── config.py                # Settings
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Dashboard home
│   │   │   ├── leads/page.tsx       # Leads management
│   │   │   ├── campaigns/           # Campaign pages
│   │   │   ├── approval/page.tsx    # Email approval
│   │   │   └── settings/page.tsx    # Settings
│   │   └── components/
│   │       ├── Sidebar.tsx          # Navigation
│   │       └── StatsCard.tsx        # Stats display
│   └── package.json
└── docker-compose.yml
```

## Legal & Compliance

- **CAN-SPAM:** All emails include unsubscribe link and physical address
- **TCPA:** Calls require prior express consent; limit automated calling
- **Data Privacy:** Scraped data is used only for outreach; honor opt-outs
- **Rate Limiting:** Built-in daily limits for emails and calls
- **Human Review:** Default setting requires manual approval before sending

⚠️ **Important:** Consult with legal counsel before running outreach at scale.

## License

MIT
