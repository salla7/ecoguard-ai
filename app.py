
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timezone

st.set_page_config(
    page_title="EcoGuard AI",
    page_icon="🌍",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #0b1220;
    color: #e5edf7;
}
[data-testid="stMetric"] {
    background: #131f32;
    border: 1px solid #26364d;
    padding: 16px;
    border-radius: 14px;
}
section[data-testid="stSidebar"] {
    background: #101a2a;
}
h1, h2, h3 {
    color: #66e3c4;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 EcoGuard AI")
st.caption(
    "Environmental Intelligence · Data Analytics · Cybersecurity"
)

st.info(
    "Air quality uses atmospheric model data and forecasts, "
    "not local sensor readings. Water and security analyses "
    "require datasets supplied by the user. This is an "
    "educational prototype, not a certified monitoring system."
)

@st.cache_data(ttl=1800)
def find_city(city):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": city,
            "count": 5,
            "language": "en",
            "format": "json"
        },
        timeout=20
    )
    response.raise_for_status()
    return response.json().get("results", [])

@st.cache_data(ttl=1800)
def get_air_quality(latitude, longitude):
    response = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "pm2_5,pm10,nitrogen_dioxide,"
                "ozone,european_aqi"
            ),
            "forecast_days": 5,
            "timezone": "auto"
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def download_csv(data, filename):
    st.download_button(
        "Download CSV results",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv"
    )

with st.sidebar:
    st.title("Control Center")
    page = st.radio(
        "Choose a module",
        [
            "Air Quality",
            "Water Quality",
            "Cybersecurity Logs",
            "About & Sources"
        ]
    )
    st.divider()
    st.caption("EcoGuard AI · Open-source prototype")

if page == "Air Quality":
    st.header("🌫️ Air Quality Intelligence")
    city = st.text_input("Enter a city", "Khenifra, Morocco")

    if st.button("Retrieve air quality data", type="primary"):
        try:
            with st.spinner("Searching for the location..."):
                locations = find_city(city.strip())

            if locations:
                st.session_state["locations"] = locations
            else:
                st.warning("Location not found. Try another city.")
        except requests.RequestException as error:
            st.error(f"Could not retrieve location: {error}")

    locations = st.session_state.get("locations", [])

    if locations:
        labels = [
            f"{item['name']}, {item.get('country', '')} "
            f"({item['latitude']:.3f}, {item['longitude']:.3f})"
            for item in locations
        ]

        selected_label = st.selectbox("Confirm location", labels)
        selected = locations[labels.index(selected_label)]

        try:
            with st.spinner("Retrieving atmospheric data..."):
                payload = get_air_quality(
                    selected["latitude"],
                    selected["longitude"]
                )

            hourly = payload.get("hourly", {})
            if not hourly.get("time"):
                st.warning("No hourly data returned.")
            else:
                data = pd.DataFrame(hourly)
                data["time"] = pd.to_datetime(
                    data["time"], errors="coerce"
                )
                data = data.dropna(subset=["time"])

                st.caption(
                    f"Location: {selected['name']}, "
                    f"{selected.get('country', '')}"
                )

                first = data.iloc[0]
                col1, col2, col3 = st.columns(3)

                for col, key, label, unit in [
                    (col1, "pm2_5", "PM2.5", "µg/m³"),
                    (col2, "pm10", "PM10", "µg/m³"),
                    (col3, "european_aqi", "European AQI", "")
                ]:
                    value = first.get(key)
                    if pd.notna(value):
                        col.metric(label, f"{value:.1f} {unit}")
                    else:
                        col.metric(label, "Unavailable")

                st.subheader("Indicator analysis")
                indicators = [
                    key for key in [
                        "pm2_5",
                        "pm10",
                        "nitrogen_dioxide",
                        "ozone",
                        "european_aqi"
                    ]
                    if key in data.columns and data[key].notna().any()
                ]

                if indicators:
                    indicator = st.selectbox(
                        "Select an indicator", indicators
                    )
                    fig = px.line(
                        data,
                        x="time",
                        y=indicator,
                        title=f"{indicator} over time",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    values = data[indicator].dropna()
                    if len(values) >= 8 and values.std() > 0:
                        mean = values.mean()
                        std = values.std()
                        anomalies = data[
                            (data[indicator] - mean).abs() > 2.5 * std
                        ]

                        st.subheader("Statistical anomaly screening")
                        st.write(
                            f"{len(anomalies)} unusual time point(s) "
                            "compared with this dataset's average."
                        )
                        if not anomalies.empty:
                            st.dataframe(
                                anomalies, use_container_width=True
                            )

                        st.caption(
                            "An unusual value is not proof of danger "
                            "or a health emergency."
                        )

                st.subheader("Retrieved data")
                st.dataframe(data, use_container_width=True)
                download_csv(data, "ecoguard_air_quality.csv")

                st.markdown(
                    "[Open-Meteo Air Quality API]"
                    "(https://open-meteo.com/en/docs/air-quality-api)"
                )
                st.caption(
                    "These values may be model estimates or forecasts, "
                    "not live local sensor measurements."
                )

        except (requests.RequestException, ValueError, KeyError) as error:
            st.error(f"Data processing failed: {error}")

elif page == "Water Quality":
    st.header("💧 Water Quality Analytics")
    st.write(
        "Upload a real CSV dataset from a laboratory, monitoring "
        "station, or research project."
    )
    st.caption(
        "Example columns: timestamp, pH, temperature, turbidity, "
        "conductivity, dissolved_oxygen."
    )

    file = st.file_uploader(
        "Upload water measurements",
        type=["csv"],
        key="water_file"
    )

    if file:
        try:
            water = pd.read_csv(file)
            st.subheader("Dataset preview")
            st.dataframe(water.head(200), use_container_width=True)

            numeric = water.select_dtypes(
                include="number"
            ).columns.tolist()

            if numeric:
                indicator = st.selectbox(
                    "Choose a numeric indicator", numeric
                )
                series = water[indicator].dropna()

                if not series.empty:
                    a, b, c = st.columns(3)
                    a.metric("Measurements", len(series))
                    b.metric("Average", f"{series.mean():.3f}")
                    c.metric(
                        "Missing values",
                        int(water[indicator].isna().sum())
                    )

                    x_axis = (
                        "timestamp"
                        if "timestamp" in water.columns
                        else water.columns[0]
                    )

                    fig = px.line(
                        water,
                        x=x_axis,
                        y=indicator,
                        title=f"{indicator} analysis",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    download_csv(water, "ecoguard_water_analysis.csv")
            else:
                st.warning("No numeric columns were found.")

            st.caption(
                "Results are statistical summaries. Water safety "
                "requires verified units and applicable standards."
            )

        except Exception as error:
            st.error(f"Could not read the CSV: {error}")

elif page == "Cybersecurity Logs":
    st.header("🛡️ Cybersecurity Log Analyzer")
    st.write(
        "Upload CSV logs from a system you own or are authorised "
        "to monitor. This module does not monitor networks live."
    )
    st.caption(
        "Useful columns include timestamp, source_ip, event, "
        "message, and status."
    )

    file = st.file_uploader(
        "Upload authorised security logs",
        type=["csv"],
        key="security_file"
    )

    if file:
        try:
            logs = pd.read_csv(file)
            st.subheader("Log preview")
            st.dataframe(logs.head(200), use_container_width=True)

            text_columns = logs.select_dtypes(
                include=["object", "string"]
            ).columns.tolist()

            if text_columns:
                column = st.selectbox(
                    "Choose the event-description column",
                    text_columns
                )

                pattern = (
                    r"failed login|authentication failure|"
                    r"unauthori[sz]ed|access denied|"
                    r"multiple login failures"
                )

                matches = logs[column].astype(str).str.contains(
                    pattern,
                    case=False,
                    regex=True,
                    na=False
                )
                flagged = logs[matches]

                st.metric("Events requiring review", len(flagged))

                if flagged.empty:
                    st.success(
                        "No matching keywords found. "
                        "This does not prove the system is secure."
                    )
                else:
                    st.warning(
                        "Review these events manually. "
                        "Keyword matches do not prove an attack."
                    )
                    st.dataframe(
                        flagged, use_container_width=True
                    )
                    download_csv(
                        flagged, "ecoguard_flagged_events.csv"
                    )
            else:
                st.warning("No text columns were found.")

            st.caption(
                "Remove passwords, access tokens, and unnecessary "
                "personal information before uploading logs."
            )

        except Exception as error:
            st.error(f"Log analysis failed: {error}")

else:
    st.header("About EcoGuard AI")
    st.write(
        "EcoGuard AI is an open-source educational project "
        "combining environmental analytics and cybersecurity "
        "log review."
    )

    st.subheader("Project modules")
    st.markdown("""
    - **Environmental intelligence:** air-quality data and charts.
    - **Statistical analysis:** basic unusual-value screening.
    - **Water analytics:** summaries of uploaded measurements.
    - **Cybersecurity:** keyword-based review of authorised logs.
    - **Data export:** download results as CSV.
    """)

    st.subheader("Data sources")
    st.markdown("""
    - Air quality: [Open-Meteo API](https://open-meteo.com/en/docs/air-quality-api)
    - Geocoding: [Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api)
    """)

    st.warning(
        "This prototype is not a trained AI model, a certified "
        "environmental system, or a live intrusion detection system."
    )

    st.write(
        "Before commercial use, review the data provider's "
        "current terms and attribution requirements."
    )

st.divider()
st.caption(
    "EcoGuard AI · Open-source prototype · "
    + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
)
