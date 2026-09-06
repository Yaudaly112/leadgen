# 🚀 Production Deployment Guide

## Prerequisites

- A VPS (Hetzner CPX21 €8/mo, DigitalOcean $12/mo, or Linode $12/mo)
- Ubuntu 22.04 or 24.04
- A domain name pointed to your server IP
- SSH access to the server

---

## Step 1: Server Setup (one-time)

SSH into your server and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version

# Log out and back in for group changes
exit
```

## Step 2: Clone the Repository

```bash
# Clone to /opt
sudo mkdir -p /opt/leadgen
cd /opt/leadgen
git clone https://github.com/yourusername/leadgen-ai.git .
```

## Step 3: Configure Environment

```bash
# Copy the production template
cp backend/.env.production backend/.env

# Edit with your values
nano backend/.env
```

**Critical values to fill in:**

| Variable | Where to get it |
|----------|----------------|
| `DATABASE_URL` | Will use internal Docker networking (see below) |
| `REDIS_PASSWORD` | Generate: `openssl rand -base64 32` |
| `POSTGRES_PASSWORD` | Same as above, or different |
| `GOOGLE_PLACES_API_KEY` | Google Cloud Console |
| `OPENAI_API_KEY` | platform.openai.com |
| `SENDGRID_API_KEY` | app.sendgrid.com |
| `EMAIL_FROM_ADDRESS` | Your verified sender email |
| `DOMAIN` | Your domain (e.g., leadgen.youragency.com) |
| `SECRET_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |

## Step 4: Configure DNS

In your DNS provider (Cloudflare, Namecheap, etc.):

```
Type    Name                    Value               TTL
A       youragency.com          1.1.1.1             300
CNAME   demo.youragency.com     youragency.com      300
```

Replace `1.1.1.1` with your server's public IP.

## Step 5: Update Caddyfile

```bash
# Edit the domain in Caddyfile
nano Caddyfile

# Change: {$DOMAIN:leadgen.yourdomain.com}
# To:     {$DOMAIN:youragency.com}
```

## Step 6: Deploy

```bash
cd /opt/leadgen

# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Watch the logs
docker compose -f docker-compose.prod.yml logs -f

# Verify all services are healthy
docker compose -f docker-compose.prod.yml ps
```

You should see:
```
NAME               STATUS
leadgen-backend-1  running (healthy)
leadgen-worker-1   running
leadgen-beat-1     running
leadgen-frontend-1 running (healthy)
leadgen-postgres-1 running (healthy)
leadgen-redis-1    running (healthy)
leadgen-caddy-1    running
```

## Step 7: Verify It Works

```bash
# Check health endpoint
curl https://youragency.com/health

# Check readiness (database + Redis)
curl https://youragency.com/health/ready

# Open the dashboard
open https://youragency.com
```

## Step 8: Configure SendGrid

1. Go to [SendGrid Settings → Mail Settings → Event Webhook](https://app.sendgrid.com/settings/mail_settings)
2. Set **HTTP Post URL** to: `https://youragency.com/api/webhooks/sendgrid`
3. Enable: Delivered, Opened, Clicked, Bounced, Dropped, Spam Reports, Unsubscribes
4. Set **Authorization Header** to: `Bearer your_sendgrid_webhook_secret`

## Step 9: Verify Email Deliverability

```bash
# Test the unsubscribe endpoint
curl "https://youragency.com/unsubscribe?email=test@test.com"

# Check email spam score at https://www.mail-tester.com
# Send a test email from your app and check the score
```

---

## Useful Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker

# Restart a service
docker compose -f docker-compose.prod.yml restart backend

# Update after git pull
cd /opt/leadgen && git pull
docker compose -f docker-compose.prod.yml up -d --build

# Database migration (if using Alembic)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Backup database
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U leadgen leadgen > backup.sql

# Check disk usage
docker system df
```

## Monitoring

```bash
# Real-time resource usage
docker stats

# Check service health
curl https://youragency.com/health/ready

# If using Sentry, errors appear at: https://sentry.io
# If using Prometheus, metrics at: https://youragency.com/api/metrics
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Caddy not getting SSL cert | Ensure DNS A record points to server IP, wait 5 min |
| Backend won't start | Check `docker compose logs backend` — usually a missing env var |
| Emails not sending | Verify SendGrid API key + sender domain authentication |
| Pipeline times out | Increase `task_time_limit` in tasks.py (default 300s) |
| Redis connection refused | Check `REDIS_PASSWORD` matches in .env and Redis service |
| Database connection refused | Check `POSTGRES_PASSWORD` matches, ensure postgres is healthy |
