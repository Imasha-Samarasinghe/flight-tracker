import json
import logging
import os
import boto3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

KAFKA_TOPIC = "flights"
KAFKA_SERVER = "localhost:9092"
BATCH_SIZE = 100   # insert to DB every 100 messages

DB_CONFIG = dict(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# AWS S3 CLIENT
# ─────────────────────────────────────────

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def create_table(conn):
    """Create flights table if it doesn't exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS flight_positions (
        id               SERIAL PRIMARY KEY,
        icao24           VARCHAR(10),
        callsign         VARCHAR(20),
        origin_country   VARCHAR(100),
        longitude        NUMERIC(9, 4),
        latitude         NUMERIC(9, 4),
        baro_altitude_m  NUMERIC(10, 2),
        geo_altitude_m   NUMERIC(10, 2),
        on_ground        BOOLEAN,
        velocity_ms      NUMERIC(8, 2),
        heading_deg      NUMERIC(6, 2),
        vertical_rate_ms NUMERIC(8, 2),
        fetched_at       TIMESTAMP WITH TIME ZONE,
        inserted_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    logger.info("Table 'flight_positions' ready in AWS RDS")


def insert_batch(conn, batch: list[dict]):
    """Bulk insert a batch of flight records into RDS."""
    columns = [
        "icao24", "callsign", "origin_country",
        "longitude", "latitude",
        "baro_altitude_m", "geo_altitude_m",
        "on_ground", "velocity_ms",
        "heading_deg", "vertical_rate_ms",
        "fetched_at",
    ]

    values = [
        tuple(flight.get(col) for col in columns)
        for flight in batch
    ]

    sql = f"""
        INSERT INTO flight_positions ({', '.join(columns)})
        VALUES %s
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, values)
        conn.commit()


# ─────────────────────────────────────────
# AWS S3 ARCHIVE
# ─────────────────────────────────────────

def archive_to_s3(batch: list[dict]):
    """
    Save a batch of raw flight events to S3 as a JSON file.
    Organised by date/hour so it's easy to query later.
    """
    now = datetime.now(timezone.utc)

    # Partition by date and hour — like a real data lake
    key = (
        f"raw/flights/"
        f"year={now.year}/"
        f"month={now.month:02d}/"
        f"day={now.day:02d}/"
        f"hour={now.hour:02d}/"
        f"batch_{now.strftime('%H-%M-%S')}.json"
    )

    body = json.dumps(batch, indent=2).encode("utf-8")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
    )

    logger.info(f"Archived {len(batch)} events to s3://{S3_BUCKET}/{key}")


# ─────────────────────────────────────────
# MAIN CONSUMER LOOP
# ─────────────────────────────────────────

def run_consumer():
    logger.info("Connecting to AWS RDS...")
    conn = get_db_connection()
    create_table(conn)

    logger.info("Starting Kafka consumer...")
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_SERVER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="flight-consumer-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    logger.info(f"Listening on topic: {KAFKA_TOPIC}")
    logger.info(f"Will batch insert every {BATCH_SIZE} messages")

    batch = []
    total_processed = 0

    for message in consumer:
        flight = message.value
        batch.append(flight)

        # When batch is full — write to RDS and S3
        if len(batch) >= BATCH_SIZE:
            try:
                insert_batch(conn, batch)
                archive_to_s3(batch)

                total_processed += len(batch)
                logger.info(
                    f"Batch written — "
                    f"{len(batch)} records | "
                    f"total: {total_processed:,}"
                )

            except Exception as e:
                logger.error(f"Batch failed: {e}")
                conn = get_db_connection()  # reconnect on error

            finally:
                batch = []  # always clear the batch


if __name__ == "__main__":
    run_consumer()
