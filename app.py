# import streamlit as st
# import folium
# from streamlit_folium import folium_static

# from gtfs_realtime import get_realtime_data, calculate_arrival_delays
# import time

# # Page Layout
# st.set_page_config(layout="wide")


# # Sidebar for Route Selection
# st.sidebar.title("🚍 Select a Route")
# route_options = static_stops["route_short_name"].unique().tolist()
# selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)

# # Fetch Realtime GTFS Data
# st.sidebar.write("🔄 Refreshing every 15 seconds...")
# realtime_df, error_msg = get_realtime_data()

# # Layout: Map (2/3 width) + Table (1/3 width)
# col1, col2 = st.columns([2, 1])

# # Initialize Map (Grey Base Map)
# m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# # Highlight Selected Route
# if selected_route != "None":
#     selected_route_id = static_stops.loc[static_stops["route_short_name"] == selected_route, "route_id"].values[0]

#     # Get route shape
#     route_shape = shapes_df[shapes_df["shape_id"].str.contains(selected_route_id, na=False)]
    
#     if not route_shape.empty:
#         route_coords = list(zip(route_shape["shape_pt_lat"], route_shape["shape_pt_lon"]))
#         folium.PolyLine(route_coords, color="blue", weight=4).add_to(m)

#     # Filter real-time vehicles on selected route
#     realtime_filtered = realtime_df[realtime_df["route_id"] == selected_route_id]

#     # Add real-time vehicle positions
#     for _, row in realtime_filtered.iterrows():
#         folium.Marker(
#             location=[row["lat"], row["lon"]],
#             popup=f"Vehicle ID: {row['vehicle_id']}<br>Speed: {row['speed']} km/h",
#             icon=folium.Icon(color="red"),
#         ).add_to(m)

# # Display Map
# with col1:
#     folium_static(m)

# # Merge Static and Realtime Data for Delay Calculation
# if not realtime_df.empty:
#     delay_df = calculate_arrival_delays(static_stops, realtime_df)
# else:
#     delay_df = static_stops  # Show static data if no real-time data available

# # Display Data Table
# with col2:
#     st.write("### 📊 Route Data with Arrival Delays")
#     if error_msg:
#         st.error(error_msg)
#     else:
#         st.dataframe(delay_df[["route_short_name", "stop_sequence", "arrival_time", "departure_time", "realtime_timestamp", "arrival_delay"]])

# # Auto Refresh Every 15 Seconds
# time.sleep(15)
# st.experimental_rerun()


import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import time
from gtfs_static import load_static_gtfs

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

# # Placeholder for static GTFS stops data
# static_stops = pd.DataFrame({
#     "Trip ID": ["trip_1", "trip_2"],
#     "Stop ID": ["stop_101", "stop_102"],
#     "arrival_time": ["12:30:00", "13:00:00"]
# })
# Load Static GTFS Data
static_stops, shapes_df = load_static_gtfs()


# Sidebar Route Selection
st.sidebar.title("🚍 Select a Route")
route_options = static_stops["Trip ID"].unique().tolist()
selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)

st.sidebar.write("🔄 Refreshing every 15 seconds...")

# Fetch Realtime GTFS Data
realtime_data, error = get_realtime_data()
if error:
    st.error(error)
else:
    st.write("Real-time Vehicle Positions:")
    st.dataframe(realtime_data)

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

# Merge and Display Data
if not realtime_data.empty:
    merged_data = merge_static_realtime(static_stops, realtime_data)
    with col2:
        st.write("### 📊 Route Data with Arrival Delays")
        st.dataframe(merged_data)

# Auto Refresh Every 15 Seconds
time.sleep(15)
st.experimental_rerun()

