import streamlit as st
import pandas as pd
import requests
import zipfile
import io
import folium
from streamlit_folium import folium_static
from google.transit import gtfs_realtime_pb2
from datetime import datetime, timedelta
import time
import pytz
import pydeck as pdk

# GTFS Static Data URL
GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"

def download_gtfs():
    """Download GTFS ZIP file and return as an in-memory object."""
    try:
        response = requests.get(GTFS_ZIP_URL, timeout=10)
        response.raise_for_status()
        return zipfile.ZipFile(io.BytesIO(response.content))
    except requests.RequestException as e:
        st.error(f"Error downloading GTFS data: {e}")
        return None

def extract_file(zip_obj, filename):
    """Extract a file from GTFS ZIP archive and return as a DataFrame."""
    try:
        with zip_obj.open(filename) as file:
            return pd.read_csv(file, dtype=str, low_memory=False)
    except Exception as e:
        return pd.DataFrame()

def load_gtfs_data():
    """Load GTFS data."""
    zip_obj = download_gtfs()
    if not zip_obj:
        return None, None, None, None, None

    routes_df = extract_file(zip_obj, "routes.txt")
    stops_df = extract_file(zip_obj, "stops.txt")
    trips_df = extract_file(zip_obj, "trips.txt")
    stop_times_df = extract_file(zip_obj, "stop_times.txt")
    shapes_df = extract_file(zip_obj, "shapes.txt")
    
    return routes_df, stops_df, trips_df, stop_times_df, shapes_df

def fetch_gtfs_rt(url):
    """Fetch GTFS-RT data."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None

def get_realtime_vehicles():
    """Fetch real-time vehicle positions."""
    feed = gtfs_realtime_pb2.FeedMessage()
    content = fetch_gtfs_rt("https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus")
    if not content:
        return pd.DataFrame()
    
    feed.ParseFromString(content)
    vehicles = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            vehicles.append({
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "vehicle_id": vehicle.vehicle.label,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "status": vehicle.current_status,
                "timestamp": datetime.fromtimestamp(vehicle.timestamp, pytz.timezone('Australia/Brisbane')).strftime('%Y-%m-%d %H:%M:%S %Z') if vehicle.HasField("timestamp") else "Unknown"
            })
    return pd.DataFrame(vehicles)

def plot_map(vehicles_df, route_shapes=None, route_stops=None):
    """Plot real-time vehicles and optionally route path on a map."""
    map_center = [vehicles_df["lat"].mean(), vehicles_df["lon"].mean()] if not vehicles_df.empty else [-27.5, 153.0]
    m = folium.Map(location=map_center, zoom_start=12)
    
    for _, row in vehicles_df.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            icon=folium.Icon(color="blue", icon="bus", prefix="fa"),
            popup=f"Vehicle {row['vehicle_id']} on Route {row['route_id']}"
        ).add_to(m)
    
    if route_shapes is not None and not route_shapes.empty:
        for _, row in route_shapes.iterrows():
            folium.PolyLine(
                [[row["shape_pt_lat"], row["shape_pt_lon"]], [row["next_lat"], row["next_lon"]]],
                color="red",
                weight=3
            ).add_to(m)
    
    folium_static(m)

# Streamlit UI
st.title("Public Transport Real-Time and Static Data Visualization")

routes_df, stops_df, trips_df, stop_times_df, shapes_df = load_gtfs_data()
vehicles_df = get_realtime_vehicles()

if not vehicles_df.empty:
    route_options = ["All Routes"] + sorted(vehicles_df["route_id"].unique())
    selected_route = st.selectbox("Select a Route", route_options)
    
    if selected_route != "All Routes" and trips_df is not None:
        directions = trips_df[trips_df["route_id"] == selected_route]["direction_id"].unique()
        selected_direction = st.radio("Select Direction", directions)
        
        route_shapes = shapes_df[shapes_df["shape_id"].isin(
            trips_df[(trips_df["route_id"] == selected_route) & (trips_df["direction_id"] == str(selected_direction))]["shape_id"].unique()
        )]
        
        if not route_shapes.empty:
            route_shapes = route_shapes.sort_values(by=["shape_id", "shape_pt_sequence"])
            route_shapes["next_lat"] = route_shapes["shape_pt_lat"].shift(-1)
            route_shapes["next_lon"] = route_shapes["shape_pt_lon"].shift(-1)
            route_shapes.dropna(subset=["next_lat", "next_lon"], inplace=True)
            
        plot_map(vehicles_df[vehicles_df["route_id"] == selected_route], route_shapes)
    else:
        plot_map(vehicles_df)
