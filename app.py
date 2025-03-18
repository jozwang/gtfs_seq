import streamlit as st
import folium
from streamlit_folium import folium_static
from gtfs_static import load_static_gtfs
from gtfs_realtime import get_realtime_vehicles, get_trip_updates
import time

# Set up page layout
st.set_page_config(layout="wide")
st.title("🚍 Real-time GTFS Tracker (TransLink)")

# Load GTFS Data
static_stops = load_static_gtfs()

# Sidebar Route Selection
st.sidebar.title("🚍 Select a Route")
route_options = static_stops["route_short_name"].dropna().unique().tolist()
selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)

# Fetch real-time vehicle positions & trip updates
st.sidebar.write("🔄 Refreshing every 15 seconds...")
realtime_df, error_msg = get_realtime_vehicles()
trip_updates_df, trip_update_err = get_trip_updates()

# Initialize Map
m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# Highlight Selected Route
if selected_route != "None":
    filtered_stops = static_stops[static_stops["route_short_name"] == selected_route]
    
    for _, row in filtered_stops.iterrows():
        folium.Marker(
            location=[float(row["stop_lat"]), float(row["stop_lon"])],
            popup=f"Stop: {row['stop_name']} (ID: {row['stop_id']})",
            icon=folium.Icon(color="blue"),
        ).add_to(m)

    # Filter real-time vehicles for the selected route
    realtime_filtered = realtime_df[realtime_df["route_id"] == filtered_stops.iloc[0]["route_id"]]

    for _, row in realtime_filtered.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=f"Vehicle: {row['vehicle_id']}<br>Speed: {row['speed']} km/h",
            icon=folium.Icon(color="red"),
        ).add_to(m)

# Display Map
folium_static(m)

# Display Trip Updates
st.write("### 🚦 Trip Updates & Delays")
if not trip_updates_df.empty:
    st.dataframe(trip_updates_df)
else:
    st.write("No trip updates available.")

# Auto-refresh every 15 seconds
time.sleep(15)
st.experimental_rerun()
