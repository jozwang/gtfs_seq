import streamlit as st
import folium
from streamlit_folium import folium_static
from gtfs_static import load_static_gtfs
from gtfs_realtime import get_realtime_data, calculate_arrival_delays
import time

# Page Layout
st.set_page_config(layout="wide")

# Load Static GTFS Data
static_stops, shapes_df = load_static_gtfs()

# Sidebar for Route Selection
st.sidebar.title("🚍 Select a Route")
route_options = static_stops["route_short_name"].unique().tolist()
selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)

# Fetch Realtime GTFS Data
st.sidebar.write("🔄 Refreshing every 15 seconds...")
realtime_df, error_msg = get_realtime_data()

# Layout: Map (2/3 width) + Table (1/3 width)
col1, col2 = st.columns([2, 1])

# Initialize Map (Grey Base Map)
m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# Highlight Selected Route
if selected_route != "None":
    selected_route_id = static_stops.loc[static_stops["route_short_name"] == selected_route, "route_id"].values[0]

    # Get route shape
    route_shape = shapes_df[shapes_df["shape_id"].str.contains(selected_route_id, na=False)]
    
    if not route_shape.empty:
        route_coords = list(zip(route_shape["shape_pt_lat"], route_shape["shape_pt_lon"]))
        folium.PolyLine(route_coords, color="blue", weight=4).add_to(m)

    # Filter real-time vehicles on selected route
    realtime_filtered = realtime_df[realtime_df["route_id"] == selected_route_id]

    # Add real-time vehicle positions
    for _, row in realtime_filtered.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=f"Vehicle ID: {row['vehicle_id']}<br>Speed: {row['speed']} km/h",
            icon=folium.Icon(color="red"),
        ).add_to(m)

# Display Map
with col1:
    folium_static(m)

# Merge Static and Realtime Data for Delay Calculation
if not realtime_df.empty:
    delay_df = calculate_arrival_delays(static_stops, realtime_df)
else:
    delay_df = static_stops  # Show static data if no real-time data available

# Display Data Table
with col2:
    st.write("### 📊 Route Data with Arrival Delays")
    if error_msg:
        st.error(error_msg)
    else:
        st.dataframe(delay_df[["route_short_name", "stop_sequence", "arrival_time", "departure_time", "realtime_timestamp", "arrival_delay"]])

# Auto Refresh Every 15 Seconds
time.sleep(15)
st.experimental_rerun()
