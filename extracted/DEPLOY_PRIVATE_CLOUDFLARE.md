# Abtin Distribution Suite — private cloud deployment

This package preserves the application and adds a Cloudflare Tunnel deployment variant. It does not deploy itself: a VPS and a Cloudflare Tunnel token are required. No public inbound web ports are opened by `docker-compose.private.yml`.

## Required external setup
1. Provision an Ubuntu 24.04 VPS (recommended starting size: 2 vCPU / 4 GB RAM; adjust to load). Install Docker Engine and the Compose plugin using Docker's official Ubuntu instructions: https://docs.docker.com/engine/install/ubuntu/ .
2. In Cloudflare Zero Trust, create a Cloudflare Tunnel. Add a Public Hostname on a hostname/zone you control, route it to `http://app:8000`, and use the tunnel token shown by Cloudflare. The `tunnel` and `app` containers share the `edge` network, so `app:8000` resolves from cloudflared.
3. In Zero Trust → Access → Applications, create a Self-hosted application for the exact same hostname. Add an Allow policy with Include → Emails containing only your own email address. Do not add broad email-domain or Everyone rules. Test from a private/incognito browser and with a different email.
4. Upload/extract this project on the VPS and enter the project directory (`Modiriyat-bazaryabi-shared-refactor-v6`).
5. Run `chmod +x deploy-private.sh && ./deploy-private.sh`. It generates DB/admin secrets and prompts for the Tunnel token without echoing it. The token and generated passwords are saved only to `.env` with mode 600.
6. Open the configured hostname, pass Cloudflare Access, then sign in to the app as `admin` using `ADMIN_PASSWORD` from `.env`.

## Operational checks
- Status: `docker compose -f docker-compose.private.yml ps`
- App logs: `docker compose -f docker-compose.private.yml logs --tail=150 app`
- Tunnel logs: `docker compose -f docker-compose.private.yml logs --tail=100 tunnel`
- Backups are written to the Docker volume `backups`; test restoring them before entering real business data. Keep off-server copies of backups.
- Do not commit or share `.env`. Do not expose PostgreSQL or app port 8000 publicly. Keep the original public deployment compose file unused for this private tunnel deployment.
- API docs are disabled by default (`API_DOCS_ENABLED=0`).

## Important limitation
The deployment cannot be completed from this workspace alone because it has no access to provision a VPS, sign in to your Cloudflare dashboard, create a zone/hostname, or obtain a tunnel token. This is a prepared deployment package, not a claim that a live server has already been launched. A Cloudflare `workers.dev` URL by itself is not a host for this FastAPI + PostgreSQL application; Cloudflare Tunnel needs a hostname/zone configured in your Cloudflare account.
