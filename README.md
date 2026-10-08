# Pulse

![CI](https://github.com/sinchukag/pulse/actions/workflows/ci.yml/badge.svg)

An uptime monitoring platform. Register a URL, and a background worker checks it on a schedule, records status and latency, and the API reports uptime stats.

## Architecture

```
Browser --> Caddy (HTTPS, ports 80/443) --> API (FastAPI) --> PostgreSQL
                                                                  ^
                                            Worker (httpx) -------+
```

| Service | Role |
|---|---|
| **caddy** | Reverse proxy and the only public entry point; handles HTTPS |
| **api** | FastAPI app: manage monitors, view checks and uptime stats, `/health` |
| **worker** | Background loop that checks due monitors and stores results |
| **db** | PostgreSQL 16 with a persistent volume; schema created from `db/init.sql` |

## Run it locally

Requires Docker Desktop.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Then open https://localhost/docs (accept the local certificate warning) and add a monitor:

```json
{"name": "Google", "url": "https://google.com", "interval_seconds": 30}
```

Watch the worker: `docker compose logs -f worker`

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Checks the API and database connection |
| POST | `/monitors` | Add a website to monitor |
| GET | `/monitors` | List monitors |
| GET | `/monitors/{id}/checks` | Recent results for one monitor |
| GET | `/status` | 24h uptime % and average latency per monitor |

## Design choices

- Secrets come from environment variables; `.env` is git-ignored, `.env.example` is the template.
- Containers run as a non-root user.
- API and worker wait for the database healthcheck before starting.
- The worker survives database outages and resumes on its own.
- Only Caddy exposes ports; the API and database are on a private Docker network.
- CI (GitHub Actions) builds the images from scratch and smoke-tests the full stack on every push.

## Failure experiments

See [notes.md](notes.md) for what happens when the database is stopped, restarted, and deleted.

## Roadmap

- [x] Phase 1: containerized app (Docker Compose)
- [x] Phase 2a: CI pipeline with smoke test
- [ ] Phase 2b: push images to a container registry
- [ ] Phase 3: deploy to Azure
- [ ] Later: Terraform, Kubernetes, monitoring