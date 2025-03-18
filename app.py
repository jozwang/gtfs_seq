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

def list_gtfs_files(zip_obj):
    """List all files in the GTFS ZIP archive."""
    return zip_obj.namelist()

def extract_file(zip_obj, filename):
    """Extract a file from a GTFS ZIP archive and return as a DataFrame."""
    with zip_obj.open(filename) as file:
        return pd.read_csv(file, dtype=str, low_memory=False)

def load_static_gtfs():
    """Load static GTFS data and return scheduled stops and routes."""
    zip_obj = download_gtfs()
    file_list = list_gtfs_files(zip_obj)
    
    # Extract necessary files if they exist
    routes_df = extract_file(zip_obj, "routes.txt") if "routes.txt" in file_list else pd.DataFrame()
    trips_df = extract_file(zip_obj, "trips.txt") if "trips.txt" in file_list else pd.DataFrame()
    stop_times_df = extract_file(zip_obj, "stop_times.txt") if "stop_times.txt" in file_list else pd.DataFrame()

    if not stop_times_df.empty and not trips_df.empty and not routes_df.empty:
        # Merge stop times with trip details
        enriched_stops = stop_times_df.merge(trips_df, on="trip_id", how="left")
        enriched_stops = enriched_stops.merge(routes_df, on="route_id", how="left")

        # Convert arrival times to datetime
        enriched_stops["arrival_time"] = pd.to_datetime(enriched_stops["arrival_time"], format="%H:%M:%S", errors="coerce")
    else:
        enriched_stops = pd.DataFrame()

    return enriched_stops

# Load static GTFS data
static_stops = load_static_gtfs()

# Streamlit App
st.set_page_config(layout="wide")
st.title("GTFS Realtime and Static Data Merge")

# Move Map to the Top
m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# Sidebar Route Selection
st.sidebar.title("🚍 Select a Route")
if "route_short_name" in static_stops.columns:
    route_options = static_stops["route_short_name"].dropna().unique().tolist()
    selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)
    
    # Filter stops for selected route and add to map
    if selected_route != "None":
        filtered_stops = static_stops[static_stops["route_short_name"] == selected_route]
        for _, row in filtered_stops.iterrows():
            folium.Marker(
                location=[float(row["stop_lat"]), float(row["stop_lon"])],
                popup=f"Stop: {row['stop_name']} (ID: {row['stop_id']})",
                icon=folium.Icon(color="blue"),
            ).add_to(m)

# Display Map
folium_static(m)

# Display Static GTFS Data
st.write("### 📊 Route Data Table")
if not static_stops.empty:
    table_height = min(600, len(static_stops) * 20)  # Adjust table height dynamically
    st.dataframe(static_stops, height=table_height)
else:
    st.write("No GTFS static data available.")
