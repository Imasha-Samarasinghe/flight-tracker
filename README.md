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

![Architecture](assets/archi.png)

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

# 📂 Project Structure

```text
flight-tracker/
│
├── assets/
│   ├── dashboard.png
│   └── archi.png
│
├── scripts/
│   ├── producer.py
│   ├── consumer.py
│   └── flight_dashboard.py
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
```

---

# ⚙️ How to Run

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/flight-tracker.git
cd flight-tracker
```

## 2. Create virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create a `.env` file using `.env.example`.

---

## 5. Start Kafka

```bash
docker-compose up -d
```

---

## 6. Run the producer

```bash
python scripts/producer.py
```

---

## 7. Run the consumer

```bash
python scripts/consumer.py
```

---

## 8. Start the dashboard

```bash
streamlit run scripts/flight_dashboard.py
```

Open:

```text
http://localhost:8501
```

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

# 👨‍💻 Author

Built by **Imasha Samarasinghe** as part of a data engineering learning project.