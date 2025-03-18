import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
import streamlit as st
from datetime import datetime

# Define GTFS-RT feed URL
GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"

# Function to fetch GTFS-RT vehicle positions
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

# Function to merge static GTFS data with real-time data
def merge_static_realtime(static_stops, realtime_data):
    """Merge static schedule with real-time data on trip_id and stop_id."""
    merged_df = pd.merge(static_stops, realtime_data, on=["Trip ID", "Stop ID"], how="inner")
    
    # Compute arrival delay in minutes
    if "arrival_time" in merged_df.columns and "Timestamp" in merged_df.columns:
        merged_df["Timestamp"] = pd.to_datetime(merged_df["Timestamp"], unit='s')
        merged_df["arrival_time"] = pd.to_datetime(merged_df["arrival_time"], format='%H:%M:%S')
        merged_df["arrival_delay"] = (merged_df["Timestamp"] - merged_df["arrival_time"]).dt.total_seconds() / 60
    
    return merged_df

# Streamlit App
st.title("GTFS Realtime and Static Data Merge")

# Load real-time data
realtime_data, error = get_realtime_data()
if error:
    st.error(error)
else:
    st.write("Real-time Vehicle Positions:")
    st.dataframe(realtime_data)

# Placeholder for static GTFS stops data
static_stops = pd.DataFrame({
    "Trip ID": ["trip_1", "trip_2"],
    "Stop ID": ["stop_101", "stop_102"],
    "arrival_time": ["12:30:00", "13:00:00"]
})

# Merge and display merged data
if not realtime_data.empty:
    merged_data = merge_static_realtime(static_stops, realtime_data)
    st.write("Merged Real-time & Static Schedule Data:")
    st.dataframe(merged_data)
