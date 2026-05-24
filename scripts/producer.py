import json
import time
import logging
import requests
from datetime import datetime, timezone
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

KAFKA_TOPIC = "flights"
KAFKA_SERVER = "localhost:9092"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
POLL_INTERVAL = 10   # seconds between API calls
MAX_FLIGHTS = 500  # cap per poll to avoid overloading

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────


def parse_flight(state: list) -> dict | None:
    """
    Convert OpenSky raw list into a clean named dict.
    Returns None if critical fields are missing.
    """
    try:
        lat = state[6]
        lon = state[5]
        if lat is None or lon is None:
            return None   # skip aircraft with no position

        return {
            "icao24":          state[0],
            "callsign":        (state[1] or "").strip() or "UNKNOWN",
            "origin_country":  state[2],
            "longitude":       round(lon, 4),
            "latitude":        round(lat, 4),
            "baro_altitude_m": state[7],
            "geo_altitude_m":  state[13],
            "on_ground":       state[8],
            "velocity_ms":     state[9],
            "heading_deg":     state[10],
            "vertical_rate_ms": state[11],
            "fetched_at":      datetime.now(timezone.utc).isoformat(),
        }
    except (IndexError, TypeError):
        return None


def fetch_flights() -> list[dict]:
    """Fetch all live flight states from OpenSky."""
    try:
        resp = requests.get(OPENSKY_URL, timeout=15)
        resp.raise_for_status()
        states = resp.json().get("states") or []

        flights = []
        for state in states[:MAX_FLIGHTS]:
            parsed = parse_flight(state)
            if parsed:
                flights.append(parsed)

        return flights

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenSky API error: {e}")
        return []


def run_producer():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=3,
    )

    logger.info("Producer started — polling OpenSky every 10s")
    logger.info(f"Publishing to Kafka topic: {KAFKA_TOPIC}")

    poll_count = 0

    while True:
        poll_count += 1
        logger.info(f"Poll #{poll_count} — fetching live flights...")

        flights = fetch_flights()

        if flights:
            for flight in flights:
                producer.send(KAFKA_TOPIC, flight)

            producer.flush()
            logger.info(
                f"Published {len(flights)} flight events to Kafka"
            )
        else:
            logger.warning("No flights returned — skipping this poll")

        logger.info(f"Sleeping {POLL_INTERVAL}s until next poll...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_producer()
