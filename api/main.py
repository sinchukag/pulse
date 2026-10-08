import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = ConnectionPool(os.environ["DATABASE_URL"], open=False,
                      kwargs={"row_factory": dict_row})

@asynccontextmanager
async def lifespan(app):
    pool.open()
    yield
    pool.close()

app = FastAPI(title="Pulse API", lifespan=lifespan)

class MonitorIn(BaseModel):
    name: str
    url: HttpUrl
    interval_seconds: int = 60

@app.get("/health")
def health():
    with pool.connection() as c:
        c.execute("SELECT 1")
    return {"status": "ok"}

@app.post("/monitors", status_code=201)
def create_monitor(m: MonitorIn):
    with pool.connection() as c:
        return c.execute(
            "INSERT INTO monitors (name,url,interval_seconds) VALUES (%s,%s,%s) RETURNING *",
            (m.name, str(m.url), m.interval_seconds)).fetchone()

@app.get("/monitors")
def list_monitors():
    with pool.connection() as c:
        return c.execute("SELECT * FROM monitors ORDER BY id").fetchall()

@app.get("/monitors/{mid}/checks")
def checks(mid: int, limit: int = 50):
    with pool.connection() as c:
        return c.execute(
            "SELECT * FROM checks WHERE monitor_id=%s ORDER BY checked_at DESC LIMIT %s",
            (mid, limit)).fetchall()

@app.get("/status")
def status():
    with pool.connection() as c:
        return c.execute("""
          SELECT m.id, m.name,
                 COUNT(c.*) AS checks_24h,
                 ROUND(100.0 * AVG(c.ok::int), 2) AS uptime_pct,
                 ROUND(AVG(c.latency_ms)) AS avg_latency_ms
          FROM monitors m
          LEFT JOIN checks c ON c.monitor_id = m.id
               AND c.checked_at > now() - interval '24 hours'
          GROUP BY m.id ORDER BY m.id""").fetchall()