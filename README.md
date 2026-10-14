# Pulse

**Live demo:** https://pulse-sinchu.duckdns.org/docs

![CI](https://github.com/sinchukag/pulse/actions/workflows/ci.yml/badge.svg)

An uptime monitoring platform. Register a URL, and a background worker checks it on a schedule, records status and latency, and the API reports uptime stats. Deployed on an Azure VM with HTTPS and fully automated CI/CD.

## Architecture

```
Browser --> Caddy (HTTPS, ports 80/443) --> API (FastAPI) --> PostgreSQL
                                                                  ^
                                            Worker (httpx) -------+
```

| Service | Role |
|---|---|
| **caddy** | Reverse proxy and the only public entry point; automatic HTTPS (Let's Encrypt) |
| **api** | FastAPI app: manage monitors, view checks and uptime stats, `/health` |
| **worker** | Background loop that checks due monitors and stores results |
| **db** | PostgreSQL 16 with a persistent volume; schema created from `db/init.sql` |

## CI/CD pipeline

Every push to `main` runs `.github/workflows/ci.yml`:

```
push --> build-and-test --> publish --> deploy
```

| Job | What it does |
|---|---|
| **build-and-test** | Builds the images from scratch, starts the full stack, adds a monitor, and checks the worker records a successful check |
| **publish** | Pushes the API and worker images to GitHub Container Registry (`ghcr.io`), tagged `latest` and with the commit SHA |
| **deploy** | Connects to the Azure VM over SSH, pulls the new images, and restarts the stack |

Each job runs only if the previous one passed, so a broken build is never published or deployed.

## Deployment

- **Cloud:** Azure VM (Ubuntu 22.04) in a resource group, with a static public IP
- **Network:** Azure firewall (NSG) allows only ports 22, 80 and 443
- **Domain and