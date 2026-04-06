import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px # Added for a nice forecast chart

# --- CONFIGURATION & LOGIC ---
# (In a real app, use st.secrets for the API_KEY)
API_KEY = "39a81eaad8f4d90734462eed7dfc5413"

def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == max_retries - 1: return None
    return None

def get_weather_data(location):
    # 1. Get Coords
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={API_KEY}"
    geo_data = fetch_with_retry(geo_url)
    if not geo_data: return None

    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
    city, country = geo_data[0]["name"], geo_data[0].get("country", "PH")

    # 2. Get Current Weather
    w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    w_data = fetch_with_retry(w_url)

    # 3. Get Air Quality
    aq_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aq_data = fetch_with_retry(aq_url)

    # 4. Get Forecast
    f_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    f_data = fetch_with_retry(f_url)

    return {
        "city": city, "country": country, "lat": lat, "lon": lon,
        "current": w_data, "air": aq_data, "forecast": f_data
    }

def calculate_heat_index(temp_c, humidity):
    temp_f = (temp_c * 9/5) + 32
    if temp_f < 80:
        hi_f = temp_f - (0.55 - 0.0055 * humidity) * (temp_f - 58)
    else:
        hi_f = (-42.379 + 2.04901523 * temp_f + 10.14333127 * humidity -
                0.22475541 * temp_f * humidity - 0.00683783 * temp_f**2 -
                0.05481717 * humidity**2 + 0.00122874 * temp_f**2 * humidity +
                0.00085282 * temp_f * humidity**2 - 0.00000199 * temp_f**2 * humidity**2)
    return (hi_f - 32) * 5/9

def get_hi_category(hi_c):
    if hi_c >= 54: return "EXTREME DANGER", "🔴", "#8B0000", "EMERGENCY: Suspend all activities."
    if hi_c >= 41: return "DANGER", "🟠", "#FF0000", "Stay indoors • High chance of class suspension."
    if hi_c >= 35: return "EXTREME CAUTION", "🟡", "#FFA500", "Limit outdoor activities."
    if hi_c >= 32: return "CAUTION", "🟡", "#FFD700", "Stay hydrated • Take shade breaks."
    return "NORMAL", "✅", "#4CAF50", "Safe conditions."

# --- STREAMLIT UI ---
st.set_page_config(page_title="WeatherTrack Pro", page_icon="🌤️", layout="wide")

st.title("🌤️ WeatherTrack Pro")
st.markdown("### Real-time Weather & Philippines Heat Index Monitor")

# Sidebar Search
with st.sidebar:
    st.header("Search Settings")
    location = st.text_input("Enter City Name", placeholder="e.g., Manila, Tokyo...")
    search_button = st.button("Check Weather")

if location or search_button:
    with st.spinner(f"Fetching data for {location}..."):
        data = get_weather_data(location)

    if data:
        # Process Logic
        curr = data['current']
        temp = curr['main']['temp']
        hum = curr['main']['humidity']
        hi_val = calculate_heat_index(temp, hum)
        hi_cat, hi_icon, hi_color, hi_rec = get_hi_category(hi_val)
        
        # Display Header
        st.header(f"📍 {data['city']}, {data['country']}")
        
        # Row 1: Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Temperature", f"{temp}°C")
        col2.metric("Humidity", f"{hum}%")
        col3.metric("Heat Index", f"{round(hi_val, 1)}°C")
        col4.metric("Wind", f"{round(curr['wind']['speed']*3.6, 1)} km/h")

        # Row 2: Heat Index Alert
        st.info(f"**{hi_icon} {hi_cat}**: {hi_rec}")

        # Row 3: Forecast Chart
        st.subheader("5-Day Forecast (Temperature & Heat Index)")
        forecast_list = []
        for item in data['forecast']['list']:
            f_temp = item['main']['temp']
            f_hum = item['main']['humidity']
            forecast_list.append({
                "Time": datetime.fromtimestamp(item['dt']),
                "Temp (°C)": f_temp,
                "Heat Index (°C)": round(calculate_heat_index(f_temp, f_hum), 1),
                "Condition": item['weather'][0]['main']
            })
        
        df = pd.DataFrame(forecast_list)
        fig = px.line(df, x="Time", y=["Temp (°C)", "Heat Index (°C)"], 
                      color_discrete_map={"Temp (°C)": "blue", "Heat Index (°C)": "orange"})
        st.plotly_chart(fig, use_container_width=True)

        # Row 4: Air Quality & Details
        st.divider()
        aq_col1, aq_col2 = st.columns(2)
        with aq_col1:
            st.write("### 💨 Air Quality")
            aq_val = data['air']['list'][0]['main']['aqi']
            aq_desc = {1:"Good", 2:"Fair", 3:"Moderate", 4:"Poor", 5:"Very Poor"}.get(aq_val)
            st.write(f"**Status:** {aq_desc}")
            st.write(f"**PM2.5:** {data['air']['list'][0]['components']['pm2_5']} µg/m³")
        
        with aq_col2:
            st.write("### ☀️ Sun & Visibility")
            st.write(f"**Sunrise:** {datetime.fromtimestamp(curr['sys']['sunrise']).strftime('%H:%M')}")
            st.write(f"**Sunset:** {datetime.fromtimestamp(curr['sys']['sunset']).strftime('%H:%M')}")
            st.write(f"**Visibility:** {curr.get('visibility', 0)/1000} km")

    else:
        st.error("Location not found. Please try again.")
else:
    st.write("Enter a city in the sidebar to get started!")