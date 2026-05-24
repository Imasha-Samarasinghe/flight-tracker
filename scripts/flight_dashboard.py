import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

st.set_page_config(
    page_title="Live Flight Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Theme constants ───────────────────────────────────────────────────────────

BG = "#0a0a0a"
CARD = "#111111"
BORDER = "#222222"
TEXT = "#f0f0f0"
SUBTEXT = "#888888"
ORANGE = "#f97316"
AMBER = "#f59e0b"
RED = "#dc2626"
YELLOW = "#fbbf24"

# Orange → red gradient used on all charts
FIRE_SCALE = [
    [0.00, "#fbbf24"],
    [0.35, "#f97316"],
    [0.70, "#ea580c"],
    [1.00, "#dc2626"],
]

# ── CSS (minimal — only what Streamlit can't do natively) ─────────────────────

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  #MainMenu, footer, header {{ visibility: hidden; }}
  html, body, .stApp, [data-testid="stAppViewContainer"],
  [data-testid="stHeader"], section.main {{
      background-color: {BG} !important;
      font-family: 'Inter', sans-serif;
  }}
  .block-container {{
      padding: 1rem 2rem 2rem !important;
      max-width: 100% !important;
  }}
  [data-testid="stVerticalBlock"] > div {{ background: transparent !important; }}

  /* metric overrides */
  [data-testid="stMetric"] {{
      background: {CARD};
      border: 1px solid {BORDER};
      border-radius: 12px;
      padding: 14px 16px;
  }}
  [data-testid="stMetricLabel"] {{ color: {SUBTEXT} !important; font-size:0.72rem !important; text-transform:uppercase; letter-spacing:0.5px; }}
  [data-testid="stMetricValue"] {{ color: {TEXT} !important; font-size:1.7rem !important; font-weight:800 !important; }}
  [data-testid="stMetricDelta"] {{ font-size:0.78rem !important; }}

  /* divider */
  hr {{ border-color: {BORDER} !important; margin: 0.6rem 0 !important; }}

  /* section label */
  .sec {{
      font-size: 0.78rem; font-weight: 700; color: {SUBTEXT};
      text-transform: uppercase; letter-spacing: 1px;
      margin: 1rem 0 0.5rem;
  }}
  .sec span {{ color: {ORANGE}; margin-right: 6px; }}

  /* live pill */
  .live-pill {{
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(249,115,22,0.12);
      border: 1px solid rgba(249,115,22,0.3);
      color: {ORANGE}; font-size: 0.72rem; font-weight: 700;
      padding: 3px 10px; border-radius: 20px;
      font-family: 'Inter', sans-serif;
  }}
  .dot {{
      width: 6px; height: 6px; border-radius: 50%;
      background: {ORANGE}; box-shadow: 0 0 6px {ORANGE};
      animation: blink 1.4s ease-in-out infinite;
  }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}

  /* country rows — pure streamlit markdown */
  .crow {{
      display:flex; align-items:center; gap:10px;
      padding:8px 12px; border-radius:8px; margin-bottom:5px;
      background:{CARD}; border:1px solid {BORDER};
  }}
  .crank {{ font-size:0.75rem; font-weight:700; color:#555; min-width:20px; }}
  .cname {{ font-size:0.85rem; font-weight:600; color:{TEXT}; flex:1; }}
  .cbarbg {{ width:70px; height:5px; background:#222; border-radius:3px; }}
  .cbar {{ height:5px; border-radius:3px;
           background: linear-gradient(90deg,{YELLOW},{ORANGE},{RED}); }}
  .cnum {{ font-size:0.85rem; font-weight:700; color:{ORANGE}; min-width:30px; text-align:right; }}
</style>
""", unsafe_allow_html=True)

# ── Chart layout helper ───────────────────────────────────────────────────────


def dark_fig(height=260):
    return dict(
        plot_bgcolor=CARD,
        paper_bgcolor=CARD,
        font=dict(family="Inter, sans-serif", color=TEXT, size=11),
        height=height,
        margin=dict(t=10, r=10, b=36, l=46),
        xaxis=dict(gridcolor=BORDER, zeroline=False,
                   tickfont=dict(color=SUBTEXT)),
        yaxis=dict(gridcolor=BORDER, zeroline=False,
                   tickfont=dict(color=SUBTEXT)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
    )

# ── DB config ─────────────────────────────────────────────────────────────────


DB = dict(
    host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

# ── Data loaders ──────────────────────────────────────────────────────────────


@st.cache_data(ttl=10)
def load_flights():
    sql = """
        SELECT DISTINCT ON (icao24)
            icao24, callsign, origin_country,
            latitude, longitude, baro_altitude_m,
            velocity_ms, heading_deg,
            COALESCE(on_ground, false) AS on_ground,
            fetched_at
        FROM flight_positions
        WHERE latitude  IS NOT NULL
          AND longitude IS NOT NULL
        ORDER BY icao24, fetched_at DESC;
    """
    conn = psycopg2.connect(**DB)
    df = pd.read_sql(sql, conn)
    conn.close()
    df["speed_kmh"] = (df["velocity_ms"] * 3.6).round(0)
    df["alt_km"] = (df["baro_altitude_m"] / 1000).round(1)
    return df


@st.cache_data(ttl=10)
def load_stats():
    sql = """
        SELECT
            COUNT(DISTINCT icao24)                  AS unique_aircraft,
            COUNT(DISTINCT origin_country)          AS countries,
            ROUND(AVG(baro_altitude_m)::numeric, 0) AS avg_altitude,
            ROUND(AVG(velocity_ms)::numeric, 2)     AS avg_speed_ms,
            COUNT(*)                                AS records_total
        FROM flight_positions;
    """
    conn = psycopg2.connect(**DB)
    row = pd.read_sql(sql, conn).iloc[0]
    conn.close()
    return row


@st.cache_data(ttl=10)
def load_countries():
    sql = """
        SELECT origin_country,
               COUNT(DISTINCT icao24) AS flights
        FROM (
            SELECT DISTINCT ON (icao24) icao24, origin_country
            FROM flight_positions
            ORDER BY icao24, fetched_at DESC
        ) l
        GROUP BY origin_country
        ORDER BY flights DESC LIMIT 10;
    """
    conn = psycopg2.connect(**DB)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


@st.cache_data(ttl=30)
def load_history():
    sql = """
        SELECT DATE_TRUNC('minute', fetched_at) AS minute,
               COUNT(*) AS cnt
        FROM flight_positions
        WHERE fetched_at IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC LIMIT 30;
    """
    conn = psycopg2.connect(**DB)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df.sort_values("minute")

# ── Fetch all data ────────────────────────────────────────────────────────────


flights = load_flights()
stats = load_stats()
countries = load_countries()
history = load_history()
now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")

n_aircraft = int(stats["unique_aircraft"] or 0)
n_countries = int(stats["countries"] or 0)
avg_alt = int(stats["avg_altitude"] or 0)
avg_kmh = int(float(stats["avg_speed_ms"] or 0) * 3.6)
n_records = int(stats["records_total"] or 0)

airborne = flights[flights["on_ground"] == False]
on_ground = flights[flights["on_ground"] == True]

# ── Header row ────────────────────────────────────────────────────────────────

h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(
        f"# ✈️ Live Flight Tracker",
    )
    st.markdown(
        f"Real aircraft · Real positions "
    )
with h2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="live-pill"><span class="dot"></span>'
        f'LIVE &nbsp;{now_str}</div>',
        unsafe_allow_html=True
    )

st.divider()

# ── KPI metrics ───────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("✈️  Live aircraft",  f"{n_aircraft:,}")
k2.metric("🌍  Countries",       f"{n_countries}")
k3.metric("🏔️  Avg altitude",   f"{avg_alt:,} m")
k4.metric("⚡  Avg speed",       f"{avg_kmh:,} km/h")
k5.metric("🗄️  Total records",  f"{n_records:,}")

st.divider()

# ── World map (full width) ────────────────────────────────────────────────────

st.markdown('<p class="sec"><span>◈</span>LIVE AIRCRAFT POSITIONS — dot colour = altitude</p>',
            unsafe_allow_html=True)

if not airborne.empty:
    fig_map = go.Figure()
    fig_map.add_trace(go.Scattergeo(
        lat=airborne["latitude"],
        lon=airborne["longitude"],
        mode="markers",
        marker=dict(
            size=3.5,
            color=airborne["baro_altitude_m"].fillna(0),
            colorscale=FIRE_SCALE,
            cmin=0, cmax=13000,
            colorbar=dict(
                title=dict(text="Alt (m)",
                           font=dict(color=SUBTEXT, size=10)),
                thickness=10, len=0.65, x=1.005,
                tickfont=dict(color=SUBTEXT, size=9),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)",
            ),
            opacity=0.9, line=dict(width=0),
        ),
        customdata=airborne[[
            "callsign", "origin_country", "alt_km", "speed_kmh"
        ]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "%{customdata[1]}<br>"
            "Altitude: %{customdata[2]} km<br>"
            "Speed: %{customdata[3]} km/h"
            "<extra></extra>"
        ),
    ))
    fig_map.update_layout(
        geo=dict(
            showland=True,       landcolor="#1a1008",
            showocean=True,      oceancolor=BG,
            showcoastlines=True, coastlinecolor="#2a1a08",
            showcountries=True,  countrycolor="#1a1208",
            showframe=False,     bgcolor=BG,
            projection_type="natural earth",
            lataxis_range=[-65, 85],
        ),
        paper_bgcolor=BG,
        margin=dict(t=0, b=0, l=0, r=0),
        height=480,
    )
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ── Row 2: countries | altitude hist | speed hist ─────────────────────────────

col1, col2, col3 = st.columns([1.1, 1, 1])

with col1:
    st.markdown('<p class="sec"><span>◈</span>TOP COUNTRIES</p>',
                unsafe_allow_html=True)
    if not countries.empty:
        mx = int(countries["flights"].max())
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, row in countries.iterrows():
            rank = i + 1
            pct = int(row["flights"] / mx * 100)
            icon = medals.get(rank, str(rank))
            st.markdown(f"""
            <div class="crow">
              <div class="crank">{icon}</div>
              <div class="cname">{row['origin_country']}</div>
              <div class="cbarbg"><div class="cbar" style="width:{pct}%"></div></div>
              <div class="cnum">{int(row['flights'])}</div>
            </div>""", unsafe_allow_html=True)

with col2:
    st.markdown('<p class="sec"><span>◈</span>ALTITUDE DISTRIBUTION</p>',
                unsafe_allow_html=True)
    if not airborne.empty:
        fig_alt = go.Figure(go.Histogram(
            x=airborne["baro_altitude_m"],
            nbinsx=22,
            marker=dict(
                color=airborne["baro_altitude_m"],
                colorscale=FIRE_SCALE,
                line=dict(width=0),
            ),
        ))
        fig_alt.update_layout(**dark_fig(300))
        fig_alt.update_layout(
            xaxis_title="Altitude (m)",
            bargap=0.04,
        )
        st.plotly_chart(fig_alt, use_container_width=True)

with col3:
    st.markdown('<p class="sec"><span>◈</span>SPEED DISTRIBUTION</p>',
                unsafe_allow_html=True)
    if not airborne.empty:
        fig_spd = go.Figure(go.Histogram(
            x=airborne["speed_kmh"],
            nbinsx=22,
            marker=dict(
                color=airborne["speed_kmh"],
                colorscale=FIRE_SCALE,
                line=dict(width=0),
            ),
        ))
        fig_spd.update_layout(**dark_fig(300))
        fig_spd.update_layout(
            xaxis_title="Speed (km/h)",
            bargap=0.04,
        )
        st.plotly_chart(fig_spd, use_container_width=True)

st.divider()

# ── Row 3: NEW — Donut  |  NEW — Top 10 fastest ───────────────────────────────
col4, col5 = st.columns([1, 1.6])
with col4:
    st.markdown(
        '<p class="sec"><span>◈</span>AIRBORNE VS ON GROUND</p>',
        unsafe_allow_html=True
    )

    n_air = len(airborne)
    n_gnd = len(on_ground)

    fig_donut = go.Figure(go.Pie(
        labels=["Airborne", "On ground"],
        values=[n_air, n_gnd],
        hole=0.65,
        marker=dict(
            colors=[ORANGE, "#222222"],
            line=dict(color=BG, width=3),
        ),
        textfont=dict(color=TEXT, size=12),
        hovertemplate="%{label}: %{value:,}<extra></extra>",
    ))

    # Centre annotation
    fig_donut.add_annotation(
        text=f"<b>{n_air:,}</b><br><span style='font-size:11px'>airborne</span>",
        x=0.5,
        y=0.5,
        font=dict(size=22, color=ORANGE, family="Inter"),
        showarrow=False,
        align="center",
    )

    layout = dark_fig(300)

    layout["legend"] = dict(
        orientation="h",
        y=-0.08,
        x=0.5,
        xanchor="center",
        font=dict(color=TEXT, size=11),
    )

    layout["margin"] = dict(
        t=10,
        b=30,
        l=10,
        r=10,
    )

    fig_donut.update_layout(**layout)

    fig_donut.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )

    st.plotly_chart(fig_donut, use_container_width=True)

with col5:
    st.markdown('<p class="sec"><span>◈</span>TOP 10 FASTEST AIRCRAFT RIGHT NOW</p>',
                unsafe_allow_html=True)

    if not airborne.empty:
        top10 = (
            airborne[airborne["speed_kmh"] > 0]
            .nlargest(10, "speed_kmh")[
                ["callsign", "origin_country", "speed_kmh", "alt_km"]
            ]
            .reset_index(drop=True)
        )
        top10["label"] = (
            top10["callsign"].str.strip()
            + " · " + top10["origin_country"]
        )

        fig_fast = go.Figure(go.Bar(
            x=top10["speed_kmh"],
            y=top10["label"],
            orientation="h",
            marker=dict(
                color=top10["speed_kmh"],
                colorscale=FIRE_SCALE,
                line=dict(width=0),
            ),
            text=top10["speed_kmh"].astype(int).astype(str) + " km/h",
            textposition="outside",
            textfont=dict(color=SUBTEXT, size=10),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Speed: %{x:,.0f} km/h<br>"
                "<extra></extra>"
            ),
        ))
        fig_fast.update_layout(**dark_fig(300))
        fig_fast.update_layout(
            xaxis=dict(
                title="Speed (km/h)",
                title_font=dict(color=SUBTEXT),
                range=[0, top10["speed_kmh"].max() * 1.18],
            ),
            yaxis=dict(autorange="reversed"),
            margin=dict(t=10, b=36, l=10, r=80),
        )
        st.plotly_chart(fig_fast, use_container_width=True)

st.divider()

# ── Trend line (full width) ───────────────────────────────────────────────────

st.markdown('<p class="sec"><span>◈</span>AIRCRAFT TRACKED OVER TIME — last 30 minutes</p>',
            unsafe_allow_html=True)

if not history.empty:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=history["minute"], y=history["cnt"],
        mode="lines",
        fill="tozeroy",
        line=dict(color=ORANGE, width=2.5),
        fillcolor="rgba(249,115,22,0.10)",
    ))
    fig_trend.add_trace(go.Scatter(
        x=history["minute"], y=history["cnt"],
        mode="markers",
        marker=dict(size=5, color=AMBER,
                    line=dict(width=1.5, color=BG)),
        showlegend=False,
    ))
    fig_trend.update_layout(**dark_fig(190))
    fig_trend.update_layout(
        xaxis=dict(tickformat="%H:%M", gridcolor=BORDER),
        showlegend=False,
        margin=dict(t=10, b=36, l=50, r=20),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.markdown(
    f"<p style='text-align:center; font-size:0.72rem; color:{SUBTEXT};'>"
    f"Live Flight Tracker &nbsp;·&nbsp; Apache Kafka + AWS RDS + AWS S3 "
    f"&nbsp;·&nbsp; Data: OpenSky Network &nbsp;·&nbsp; Built by Imasha Samarasinghe"
    f"</p>",
    unsafe_allow_html=True,
)

# ── Auto refresh every 30s ────────────────────────────────────────────────────

st.markdown(
    "<script>setTimeout(()=>window.location.reload(),30000)</script>",
    unsafe_allow_html=True,
)
