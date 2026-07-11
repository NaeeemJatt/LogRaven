# LogRaven — AWS Free Tier Deployment Plan

Deploy the full stack (frontend, API, Celery worker, Celery beat, PostgreSQL, Redis)
on a **single EC2 instance** with `docker-compose.prod.yml`, plus **Amazon SES** for
email. This is the cheapest architecture that runs everything LogRaven needs.

---

## 1. Understand the current AWS Free Tier (important!)

AWS changed the Free Tier for accounts created **after July 15, 2025**:

| | New accounts (post 2025-07-15) | Legacy accounts (pre 2025-07-15) |
|---|---|---|
| Model | **Credits**: $100 at sign-up + up to $100 more for completing 5 console activities (EC2, RDS, Lambda, Bedrock, Budgets — $20 each) | 12 months of free usage per service |
| Duration | Free plan ends after **6 months** or when credits run out — whichever is first | 12 months |
| EC2 | Paid from credits | 750 h/month t2.micro or t3.micro |
| Always-free services | 30+ services (Lambda, DynamoDB, CloudWatch basics, SES sandbox, etc.) | Same |

**What this means for LogRaven:**
- A `t3.micro` (~$8/month) or `t3.small` (~$15/month) runs comfortably for the whole
  6-month free-plan window on the $100–$200 credits.
- On a Free account plan you are **never charged** — the account simply stops when
  credits are exhausted or 6 months pass. Upgrade to a Paid plan to keep the instance.
- Do the five "Explore AWS" activities on day one; it's 15 minutes for +$100.

> Recommended: **t3.small (2 GB RAM)** if credits allow — the AI pipeline + PDF
> generation is memory-hungry. `t3.micro` (1 GB) works with the swap file below.

---

## 2. Architecture

```
Internet ──► EC2 (t3.small, Ubuntu 24.04, Elastic IP)
              └── docker compose
                   ├── web    : nginx — serves React bundle, proxies /api /auth /health
                   ├── api    : FastAPI (runs migrations on boot, 2 uvicorn workers)
                   ├── worker : Celery worker (investigations + compliance audits)
                   ├── beat   : Celery beat (continuous monitoring, stuck-job reconciler)
                   ├── db     : PostgreSQL 15 (Docker volume)
                   └── redis  : Redis 7 (broker + refresh tokens + rate limits)
Amazon SES ──► outbound email (verification, password reset, job notifications)
S3 (optional) ─► file storage instead of the local Docker volume
```

Everything lives on one box; nothing but ports 80/443 (and 22 for you) is exposed.

---

## 3. Step-by-step

### 3.1 Account + credits (~15 min)
1. Create the AWS account, choose the **Free account plan**.
2. In the console home, open the **Explore AWS** widget and complete the five
   activities (launch/terminate an EC2 instance, RDS config walkthrough, Lambda
   function, Bedrock playground prompt, AWS Budgets alert) → **+$100 credits**.
3. In **Billing → Budgets**, create a zero-spend budget alert (safety net).

### 3.2 Launch the EC2 instance (~10 min)
1. EC2 → Launch instance:
   - **Name**: `lograven`
   - **AMI**: Ubuntu Server 24.04 LTS (64-bit x86)
   - **Type**: `t3.small` (or `t3.micro` on a tight budget)
   - **Key pair**: create one, download the `.pem`
   - **Storage**: 30 GB gp3
   - **Security group**: allow `22` (My IP only), `80`, `443` (Anywhere)
2. **Elastic IP**: EC2 → Elastic IPs → Allocate → Associate with the instance
   (free while attached to a running instance; keeps your address across restarts).

### 3.3 Prepare the server (~10 min)
```bash
ssh -i lograven.pem ubuntu@YOUR_ELASTIC_IP

# Swap file — mandatory on 1–2 GB instances
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit   # log out & back in so the docker group applies
```

### 3.4 Deploy LogRaven (~10 min)
```bash
git clone https://github.com/YOUR_USERNAME/LogRaven.git
cd LogRaven

cp .env.production.example .env
nano .env
#   JWT_SECRET_KEY      = openssl rand -hex 32
#   POSTGRES_PASSWORD   = openssl rand -hex 16
#   GEMINI_API_KEY      = your AI API key
#   FRONTEND_BASE_URL   = http://YOUR_ELASTIC_IP   (or your domain)
#   SMTP_*              = from step 3.5

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # all services healthy?
curl http://localhost/health                        # {"status": "..."}
```
Open `http://YOUR_ELASTIC_IP` — register, run an investigation, start an audit.

### 3.5 Amazon SES for email (~20 min)
1. SES → Verified identities → verify your **sender address** (or whole domain).
2. SES → SMTP settings → **Create SMTP credentials** — note the endpoint
   (e.g. `email-smtp.eu-west-1.amazonaws.com`), username, and password.
3. Put them in `.env` (`SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USERNAME`,
   `SMTP_PASSWORD`, `SMTP_FROM_EMAIL=verified@yourdomain.com`).
4. Sandbox mode only delivers to verified addresses — fine for testing. For real
   users, request **production access** (SES console → Account dashboard →
   Request production access; usually approved in ~24 h).
5. `docker compose -f docker-compose.prod.yml up -d` to reload env.

SES is effectively free at this scale (3,000 message charges/month free for the
first 12 months on the new free tier; $0.10 per 1,000 emails after).

### 3.6 Domain + HTTPS (required for a public launch, ~20 min)
1. Point a domain (Route 53, Namecheap, Cloudflare…) A-record at the Elastic IP.
2. Issue the certificate once on the host (the fixed `--cert-name lograven` is
   what `frontend/nginx-tls.conf` expects — no config editing needed):
   ```bash
   sudo apt install -y certbot
   sudo certbot certonly --standalone --cert-name lograven -d yourdomain.com
   ```
3. Set in `.env`: `FRONTEND_BASE_URL=https://yourdomain.com`, `COOKIE_SECURE=true`.
4. Start the stack with the bundled TLS overlay (terminates TLS in nginx,
   redirects 80 → 443, serves HSTS):
   ```bash
   docker compose -f docker-compose.prod.yml -f docker-compose.tls.yml up -d --build
   ```
5. After each certbot renewal, reload nginx:
   ```bash
   docker compose -f docker-compose.prod.yml -f docker-compose.tls.yml exec web nginx -s reload
   ```

### 3.7 Backups (~10 min)
```bash
# /home/ubuntu/backup.sh — nightly DB dump, keep 7 days
mkdir -p ~/backups
docker compose -f ~/LogRaven/docker-compose.prod.yml exec -T db \
  pg_dump -U postgres lograven | gzip > ~/backups/lograven-$(date +%F).sql.gz
find ~/backups -name '*.sql.gz' -mtime +7 -delete
```
`crontab -e` → `0 3 * * * /home/ubuntu/backup.sh`
Optionally sync to S3: `aws s3 sync ~/backups s3://your-backup-bucket/` (5 GB free).

**Restore drill (run once before launch, then quarterly):**
```bash
# Restore the newest dump into a scratch database and sanity-check it.
LATEST=$(ls -t ~/backups/*.sql.gz | head -1)
docker compose -f ~/LogRaven/docker-compose.prod.yml exec -T db \
  psql -U postgres -c "DROP DATABASE IF EXISTS lograven_restore; CREATE DATABASE lograven_restore;"
gunzip -c "$LATEST" | docker compose -f ~/LogRaven/docker-compose.prod.yml exec -T db \
  psql -U postgres -d lograven_restore
docker compose -f ~/LogRaven/docker-compose.prod.yml exec -T db \
  psql -U postgres -d lograven_restore -c "SELECT count(*) FROM users; SELECT count(*) FROM investigations;"
docker compose -f ~/LogRaven/docker-compose.prod.yml exec -T db \
  psql -U postgres -c "DROP DATABASE lograven_restore;"
```

**Rollback after a bad deploy:** `git checkout <last-good-commit> && docker compose -f docker-compose.prod.yml up -d --build`.
Migrations run forward automatically; if a migration itself must be undone, run
`docker compose -f docker-compose.prod.yml exec api alembic downgrade -1` before checking out the old commit.

### 3.8 Updating the app
```bash
cd ~/LogRaven && git pull
docker compose -f docker-compose.prod.yml up -d --build
```
Migrations run automatically when the `api` container boots.

---

## 4. Cost forecast (credits-based free plan)

| Item | Monthly | 6-month total |
|---|---|---|
| EC2 t3.small | ~$15.20 | ~$91 |
| EBS 30 GB gp3 | ~$2.40 | ~$14 |
| Elastic IP (attached) | $0 | $0 |
| SES (< 3k emails) | $0 | $0 |
| Data transfer (light) | ~$1 | ~$6 |
| **Total** | **~$19** | **~$111** ← inside $200 credits |

With `t3.micro` instead: ~$11/month, ~$66 total — inside even the base $100 credit.

**When credits/6-months end**: upgrade to the Paid plan (same prices, now billed),
or re-evaluate: move Postgres to RDS, storage to S3, and the API to a bigger box
as revenue justifies.

---

## 5. Production checklist

- [ ] `JWT_SECRET_KEY` and `POSTGRES_PASSWORD` are long random values
- [ ] Port 22 restricted to your IP; 5432/6379 not exposed at all
- [ ] Swap enabled (`free -h` shows 2 GB swap)
- [ ] SES production access approved; `SMTP_*` set; test "forgot password" e2e
- [ ] HTTPS live and `COOKIE_SECURE=true`
- [ ] Zero-spend / $10 budget alarm active
- [ ] Nightly `pg_dump` cron in place (verify one restore!)
- [ ] `docker compose ps` shows api healthy, worker + beat running
- [ ] CI green on GitHub before every deploy (`.github/workflows/ci.yml`)
