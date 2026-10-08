import os, time, logging
import httpx
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
DSN = os.environ["DATABASE_URL"]

DUE = """
SELECT m.id, m.url FROM monitors m
WHERE NOT EXISTS (
  SELECT 1 FROM checks c
  WHERE c.monitor_id = m.id
    AND c.checked_at > now() - make_interval(secs => m.interval_seconds))
"""

def check(client, url):
    start = time.perf_counter()
    try:
        r = client.get(url, timeout=10, follow_redirects=True)
        return r.status_code, int((time.perf_counter() - start) * 1000), r.status_code < 0
    except httpx.HTTPError:
        return None, int((time.perf_counter() - start) * 1000), False

def main():
    logging.info("worker started")
    with httpx.Client() as client:
        while True:
            try:
                with psycopg.connect(DSN, autocommit=True) as conn:
                    for mid, url in conn.execute(DUE).fetchall():
                        code, ms, ok = check(client, url)
                        conn.execute(
                            "INSERT INTO checks (monitor_id,status_code,latency_ms,ok) VALUES (%s,%s,%s,%s)",
                            (mid, code, ms, ok))
                        logging.info("monitor=%s url=%s ok=%s code=%s ms=%s", mid, url, ok, code, ms)
            except psycopg.OperationalError as e:
                logging.error("db unavailable: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    main()