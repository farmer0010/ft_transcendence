"""Idempotently provision Uptime Kuma monitors for the stack's core services.

Runs once as a short-lived init container after Uptime Kuma reports healthy.
Safe to re-run: it skips monitors that already exist by name.
"""
import os
import sys
import time

from uptime_kuma_api import MonitorType, UptimeKumaApi

KUMA_URL = os.environ.get("UPTIME_KUMA_URL", "http://uptime-kuma:3001")
ADMIN_USER = os.environ["UPTIME_KUMA_ADMIN_USER"]
ADMIN_PASSWORD = os.environ["UPTIME_KUMA_ADMIN_PASSWORD"]

MONITORS = [
    {
        "type": MonitorType.HTTP,
        "name": "backend",
        "url": "http://backend:8080/actuator/health",
        "interval": 30,
    },
    {
        "type": MonitorType.HTTP,
        "name": "ai",
        "url": "http://ai:8000/health",
        "interval": 30,
    },
    {
        "type": MonitorType.HTTP,
        "name": "nginx (public API)",
        "url": "http://nginx:80/v4/cabinets/status-summary/all",
        "interval": 30,
    },
    {
        "type": MonitorType.PORT,
        "name": "mariadb",
        "hostname": "mariadb",
        "port": 3306,
        "interval": 30,
    },
    {
        "type": MonitorType.PORT,
        "name": "redis",
        "hostname": "redis",
        "port": 6379,
        "interval": 30,
    },
]


def connect_with_retry(url: str, attempts: int = 10, delay: float = 3.0) -> UptimeKumaApi:
    last_error = None
    for i in range(attempts):
        try:
            return UptimeKumaApi(url)
        except Exception as exc:  # noqa: BLE001 - retry on any connect error
            last_error = exc
            print(f"[provision] connect attempt {i + 1}/{attempts} failed: {exc}")
            time.sleep(delay)
    raise SystemExit(f"[provision] could not connect to Uptime Kuma at {url}: {last_error}")


def main() -> int:
    api = connect_with_retry(KUMA_URL)
    try:
        if api.need_setup():
            print("[provision] running first-time setup")
            api.setup(ADMIN_USER, ADMIN_PASSWORD)

        # setup() alone doesn't establish an authenticated session (no
        # initial monitor-list push), so always log in afterwards.
        print("[provision] logging in")
        api.login(ADMIN_USER, ADMIN_PASSWORD)

        existing_names = {m["name"] for m in api.get_monitors()}
        for monitor in MONITORS:
            if monitor["name"] in existing_names:
                print(f"[provision] monitor '{monitor['name']}' already exists, skipping")
                continue
            print(f"[provision] creating monitor '{monitor['name']}'")
            api.add_monitor(**monitor)
    finally:
        api.disconnect()

    print("[provision] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
