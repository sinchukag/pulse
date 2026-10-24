import os, time, logging
import httpx
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
DSN = os.environ["DATABASE_URL"]

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
FAILS_BEFORE_ALERT = 2   # alert only after this many failed checks in a row

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
        return r.status_code, int((time.perf_counter() - start) * 1000), r.status_code < 400
    except httpx.HTTPError:
        return None, int((time.perf_counter() - start) * 1000), False

def update_state(state, mid, ok):
    """Track each monitor. Returns "down", "recovered", or None (nothing to report)."""
    s = state.setdefault(mid, {"up": True, "fails": 0})
    if ok:
        s["fails"] = 0
        if not s["up"]:
            s["up"] = True
            return "recovered"
        return None
    s["fails"] += 1
    if s["up"] and s["fails"] >= FAILS_BEFORE_ALERT:
        s["up"] = False
        return "down"
    return None

def send_alert(client, text):
    if not BOT_TOKEN or not CHAT_ID:
        return  # alerts not configured
    try:
        client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except httpx.HTTPError as e:
        # log only the error type: the message could contain the URL (and token)
        logging.error("alert failed: %s", type(e).__name__)

def main():
    logging.info("worker started")
    state = {}
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
                        event = update_state(state, mid, ok)
                        if event == "down":
                            send_alert(client, f"DOWN: {url} (status {code})")
                        elif event == "recovered":
                            send_alert(client, f"RECOVERED: {url} is back up")
            except psycopg.OperationalError as e:
                logging.error("db unavailable: %s",e)
            time.sleep(5)

if __name__ == "__main__":
    main()