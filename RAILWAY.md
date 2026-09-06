# Deploy to Railway — Step by Step

## Prerequisites

You already have:
- ✅ Google Places API key
- ✅ OpenAI API key
- ✅ SendGrid API key (from `polsia.app`)
- ✅ Neon PostgreSQL (managed)
- ✅ Redis Cloud (managed)

You need:
- 📌 A Railway account ([railway.app](https://railway.app))
- 📌 A GitHub repo with this code
- 📌 SendGrid domain authentication (see below)

---

## Step 1: Push Code to GitHub

```bash
# In your project root
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/leadgen.git
git push -u origin main
```

---

## Step 2: Authenticate SendGrid Domain (Required!)

Without this, emails land in spam.

1. Go to **[app.sendgrid.com](https://app.sendgrid.com) → Settings → Sender Authentication → Authenticate Your Domain**
2. Enter your domain: `polsia.app`
3. SendGrid gives you 3 DNS records to add at your domain registrar

### Add these DNS records at your domain registrar (where you bought polsia.app):

| Type | Host | Value |
|------|------|-------|
| TXT | `@` | `v=spf1 include:sendgrid.net ~all` |
| CNAME | `s1._domainkey` | (value from SendGrid) |
| CNAME | `s2._domainkey` | (value from SendGrid) |
| CNAME | The third record | (value from SendGrid) |

4. Wait 15 minutes for DNS propagation
5. Click **Verify** in SendGrid

### Set up SendGrid Event Webhook:
1. Go to **Settings → Mail Settings → Event Webhook**
2. **HTTP Post URL:** `https://backend-YOUR_PROJECT.up.railway.app/api/webhooks/sendgrid`
   (You'll update this after deployment — just note the URL pattern)
3. Enable events: Delivered, Opened, Clicked, Bounced, Dropped, Spam Reports, Unsubscribes
4. **Authorization Header:** `Bearer your_secret_here`

---

## Step 3: Create Railway Project

1. Go to **[railway.app](https://railway.app)** → New Project
2. Click **"Deploy from GitHub Repo"**
3. Select your `leadgen` repo
4. Railway will detect the monorepo and ask what to deploy

### Add Backend Service
1. Click **"+ New" → "Service" → "GitHub Repo"** (same repo)
2. Name it `backend`
3. Railway will auto-detect the Dockerfile at `backend/Dockerfile`
4. Go to **Settings → Build:**
   - **Dockerfile Path:** `backend/Dockerfile`
   - **Docker Context:** `backend`

### Add Frontend Service
1. Click **"+ New" → "Service" → "GitHub Repo"** (same repo)
2. Name it `frontend`
3. **Settings → Build:**
   - **Dockerfile Path:** `frontend/Dockerfile`
   - **Docker Context:** `frontend`

### Add Worker Service (Celery)
1. Click **"+ New" → "Service" → "GitHub Repo"** (same repo)
2. Name it `worker`
3. **Settings → Build:** Same as backend
4. **Settings → Deploy → Custom Start Command:**
   ```
   celery -A app.tasks worker --loglevel=info --concurrency=2
   ```

### Add Beat Service (Celery Beat Scheduler)
1. Click **"+ New" → "Service" → "GitHub Repo"** (same repo)
2. Name it `beat`
3. **Settings → Build:** Same as backend
4. **Settings → Deploy → Custom Start Command:**
   ```
   celery -A app.tasks beat --loglevel=info
   ```

---

## Step 4: Set Environment Variables

Go to **each service → Variables** tab and add:

### Backend Service Variables:
```
DATABASE_URL=postgresql+asyncpg://authenticator:npg_W6mRlHnqTuL1@ep-cold-thunder-aynnhdmv-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require

REDIS_URL=redis://default:FuqNItV0454ETgzoI0uWYw86Riah8hGP@wire-zipper-silver-51305.db.redis.io:11782

GOOGLE_PLACES_API_KEY=AIzaSyDH4MJ_n92kdShaomw0Pnly4mEwyAr2P2M

OPENAI_API_KEY=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

SENDGRID_API_KEY=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

EMAIL_FROM_ADDRESS=quirkpost-2@polsia.app
EMAIL_FROM_NAME=LeadGen AI
UNSUBSCRIBE_URL=https://polsia.app/unsubscribe

DOMAIN=polsia.app
DEMO_BASE_URL=https://demo.polsia.app

REVIEW_BEFORE_SENDING=true
MAX_EMAILS_PER_DAY=50
MAX_CALLS_PER_DAY=20

SECRET_KEY=change-this-to-something-random
FRONTEND_URL=https://frontend-YOUR_PROJECT.up.railway.app
```

### Worker + Beat Variables:
Same as backend (copy all the variables above).

### Frontend Variables:
```
BACKEND_URL=http://backend-YOUR_PROJECT.up.railway.app
NEXT_PUBLIC_API_URL=https://backend-YOUR_PROJECT.up.railway.app
```

> **Note:** Replace `YOUR_PROJECT` with your actual Railway project ID (visible in the Railway dashboard URL).

---

## Step 5: Deploy

1. Railway auto-deploys on push to `main`
2. Check the deploy logs for each service
3. The backend should show: `Uvicorn running on http://0.0.0.0:8000`
4. The frontend should show: `Ready - started on 0.0.0.0:3000`

---

## Step 6: Verify Everything Works

### Check Backend Health
```bash
curl https://backend-YOUR_PROJECT.up.railway.app/health
# Should return: {"status": "healthy", "database": "connected", "redis": "connected"}
```

### Check Frontend
Open `https://frontend-YOUR_PROJECT.up.railway.app` in your browser

### Test SendGrid Webhook
```bash
curl -X POST https://backend-YOUR_PROJECT.up.railway.app/api/webhooks/sendgrid/verify
# Should return: {"status": "ok", "message": "Webhook endpoint is reachable"}
```

### Test Email Sending
1. Open the dashboard → Create a campaign
2. Run discovery for a small area
3. Enrich a lead → Generate demo
4. Send a test email to yourself

---

## Step 7: Custom Domains (Optional)

To use your own domain instead of `*.up.railway.app`:

### Backend:
1. In Railway → Backend service → Settings → Networking
2. Click "Custom Domain" → enter `api.polsia.app`
3. Add the DNS record Railway gives you (CNAME to `xxx.up.railway.app`)
4. Update `FRONTEND_URL` to the new frontend URL

### Frontend:
1. In Railway → Frontend service → Settings → Networking
2. Click "Custom Domain" → enter `polsia.app`
3. Add the DNS record

---

## Step 8: Update SendGrid Webhook URL

Once your custom domains are live:
1. Go to SendGrid → Settings → Mail Settings → Event Webhook
2. Update **HTTP Post URL** to `https://polsia.app/api/webhooks/sendgrid`
   (or `https://backend-YOUR_PROJECT.up.railway.app/api/webhooks/sendgrid`)

---

## Cost on Railway

| Service | Plan | Monthly |
|---------|------|---------|
| Backend (512MB RAM) | Hobby | $5 |
| Frontend (256MB RAM) | Hobby | $5 |
| Worker (512MB RAM) | Hobby | $5 |
| Beat (256MB RAM) | Hobby | $5 |
| **Total Railway** | | **~$20/mo** |
| Neon PostgreSQL | Free | $0 |
| Redis Cloud | Free | $0 |
| **Grand Total** | | **~$20/mo** |

> Railway gives $5 free credit per month on the Hobby plan.
> Upgrade to the $20/mo plan for unlimited services if needed.

---

## Troubleshooting

### "Connection refused" errors
- Backend can't connect to Neon/Redis — check your DATABASE_URL and REDIS_URL
- Neon pooler requires `sslmode=require`

### Frontend shows "Loading..." forever
- The frontend can't reach the backend
- Check `BACKEND_URL` env var on the frontend service
- Make sure it starts with `http://` not `https://` (internal Railway communication)

### Emails not sending
- Check SendGrid API key is valid
- Verify domain authentication is complete
- Check backend logs for SendGrid errors

### Pipeline fails on discovery
- Google Places API key may have billing issues
- Check that Places API is enabled in Google Cloud Console
