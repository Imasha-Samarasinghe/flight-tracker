# ✈️ Live Flight Tracker

A real-time flight tracking pipeline built using Python, Apache Kafka, AWS, and Streamlit.

This project collects live aircraft data from the OpenSky API, streams it through Kafka, stores it in AWS RDS and S3, and visualises everything on a live dashboard.

![Dashboard](assets/dashboard.png)

---

# 🚀 Features

- Live aircraft tracking dashboard
- Kafka-based streaming pipeline
- AWS RDS PostgreSQL database
- AWS S3 raw data storage
- Real-time charts and analytics
- Docker setup for Kafka

---

# 🏗️ System Architecture

## How it works

![Architecture](assets/archi.png)

A producer script polls the OpenSky API every 10 seconds and pushes each
aircraft as a JSON event into a Kafka topic. A consumer reads from that topic,
batch-inserts clean records into AWS RDS, and archives the raw JSON to S3
with Hive-style partitioning. The Streamlit dashboard queries RDS and
reloads every 30 seconds.
---

# 🛠️ Technologies Used

- Python
- Apache Kafka
- Docker
- AWS RDS PostgreSQL
- AWS S3
- Streamlit
- Plotly
- OpenSky Network API

---

---

## Running it locally

```bash
git clone https://github.com/YOUR_USERNAME/flight-tracker.git
cd flight-tracker

python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# add your AWS credentials and RDS endpoint to .env

docker-compose up -d           # start Kafka

python scripts/producer.py     # terminal 1
python scripts/consumer.py     # terminal 2
streamlit run scripts/flight_dashboard.py  # terminal 3
```

Open **http://localhost:8501**

---

# ☁️ AWS Services

### AWS RDS PostgreSQL
Used to store processed flight data.

### AWS S3
Used to archive raw JSON flight records.

---

# 📊 Dashboard

The dashboard includes:

- Live world map of aircraft
- Top countries by aircraft count
- Altitude distribution
- Speed distribution
- Airborne vs on-ground comparison
- Top 10 fastest aircraft
- Aircraft trend over time

---

# 📡 Data Source

Flight data comes from:

https://opensky-network.org

---
