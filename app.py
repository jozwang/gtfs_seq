import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import time
import zipfile
import io

# GTFS Static Data URL
GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"

def download_gtfs():
    """Download GTFS ZIP file and return as an in-memory object."""
    response = requests.get(GTFS_ZIP_URL)
    if response.status_code == 200:
        return zipfile.ZipFile(io.BytesIO(response.content))
    else:
        raise Exception("Failed to download GTFS data.")

def extract_file(zip_obj, filename):
    """Extract a file from a GTFS ZIP archive and return as a DataFrame."""
    with zip_obj.open(filename) as file:
        return pd.read_csv(file)

def load_static_gtfs():
    """Load static GTFS data and return scheduled stops, routes, and shapes."""
    zip_obj = download_gtfs()

    # Extract necessary files
    routes_df = extract_file(zip_obj, "routes.txt")
    shapes_df = extract_file(zip_obj, "shapes.txt")
    trips_df = extract_file(zip_obj, "trips.txt")
    stop_times_df = extract_file(zip_obj, "stop_times.txt")

    # Merge stop times with trip details
    enriched_stops = stop_times_df.merge(trips_df, on="trip_id", how="left")
    enriched_stops = enriched_stops.merge(routes_df, on="route_id", how="left")

    # Convert arrival times to datetime
    enriched_stops["arrival_time"] = pd.to_datetime(enriched_stops["arrival_time"], format="%H:%M:%S", errors="coerce")

    return enriched_stops, shapes_df

# Define GTFS-RT feed URL
GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"

def get_realtime_data():
    """Fetch real-time GTFS-RT data and return a DataFrame."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return pd.DataFrame(), "Failed to fetch real-time data"

    feed.ParseFromString(response.content)

    vehicles = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            trip = vehicle.trip
            
            vehicles.append({
                "Vehicle ID": vehicle.vehicle.id,
                "Label": vehicle.vehicle.label,
                "Latitude": vehicle.position.latitude,
                "Longitude": vehicle.position.longitude,
                "Route ID": trip.route_id,
                "Trip ID": trip.trip_id,
                "Stop Sequence": vehicle.current_stop_sequence if vehicle.HasField("current_stop_sequence") else "Unknown",
                "Stop ID": vehicle.stop_id if vehicle.HasField("stop_id") else "Unknown",
                "Current Status": vehicle.current_status if vehicle.HasField("current_status") else "Unknown",
                "Timestamp": vehicle.timestamp if vehicle.HasField("timestamp") else "Unknown"
            })
    
    return pd.DataFrame(vehicles), None

def merge_static_realtime(static_stops, realtime_data):
    """Merge static schedule with real-time data on trip_id and stop_id."""
    merged_df = pd.merge(static_stops, realtime_data, on=["Trip ID", "Stop ID"], how="inner")
    
    if "arrival_time" in merged_df.columns and "Timestamp" in merged_df.columns:
        merged_df["Timestamp"] = pd.to_datetime(merged_df["Timestamp"], unit='s')
        merged_df["arrival_time"] = pd.to_datetime(merged_df["arrival_time"], format='%H:%M:%S')
        merged_df["arrival_delay"] = (merged_df["Timestamp"] - merged_df["arrival_time"]).dt.total_seconds() / 60
    
    return merged_df

# Streamlit App
st.set_page_config(layout="wide")
st.title("GTFS Realtime and Static Data Merge")

# Load static GTFS data
static_stops, shapes_df = load_static_gtfs()

# Fetch Realtime GTFS Data
realtime_data, error = get_realtime_data()
if error:
    st.error(error)
else:
    st.write("Real-time Vehicle Positions:")
    st.dataframe(realtime_data)

# Merge and Update Static Stops
if not realtime_data.empty:
    static_stops = merge_static_realtime(static_stops, realtime_data)

# Sidebar Route Selection
st.sidebar.title("🚍 Select a Route")
route_options = static_stops["Trip ID"].unique().tolist()
selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)

st.sidebar.write("🔄 Refreshing every 15 seconds...")

# Initialize Map
col1, col2 = st.columns([2, 1])
m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# Filter vehicles for selected route
if selected_route != "None":
    realtime_filtered = realtime_data[realtime_data["Trip ID"] == selected_route]
    for _, row in realtime_filtered.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"Vehicle ID: {row['Vehicle ID']}<br>Speed: {row.get('Speed', 'N/A')} km/h",
            icon=folium.Icon(color="red"),
        ).add_to(m)

# Display Map
with col1:
    folium_static(m)

# Display Merged Data
with col2:
    st.write("### 📊 Route Data with Arrival Delays")
    st.dataframe(static_stops)

# Auto Refresh Every 15 Seconds
time.sleep(15)
st.experimental_rerun()
