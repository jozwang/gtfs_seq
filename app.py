import streamlit as st
import folium
from streamlit_folium import folium_static
from gtfs_static import load_static_gtfs
from gtfs_realtime import get_realtime_vehicles, get_trip_updates
import time
import pandas as pd

# Set up page layout
st.set_page_config(layout="wide")
st.title("🚍 Real-time GTFS Tracker (TransLink)")

# Add a refresh button
refresh = st.sidebar.button("🔄 Refresh Data")

# Add auto-refresh checkbox
auto_refresh = st.sidebar.checkbox("Auto-refresh every 30 seconds", value=True)

# Cache static data to prevent reloading on each refresh
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_static_data():
    return load_static_gtfs()

# Load GTFS Static Data
with st.spinner("Loading static GTFS data..."):
    static_stops = get_static_data()
    
    if static_stops.empty:
        st.error("Could not load static GTFS data. Please try again later.")
        st.stop()

# Sidebar Route Selection
st.sidebar.title("🚍 Select a Route")
route_options = static_stops["route_short_name"].dropna().unique().tolist()
if route_options:
    route_options.sort()
    selected_route = st.sidebar.selectbox("Choose a Route", ["None"] + route_options)
else:
    st.error("No routes found in static data.")
    st.stop()

# Fetch real-time vehicle positions & trip updates
with st.spinner("Fetching real-time data..."):
    realtime_df = get_realtime_vehicles()
    trip_updates_df = get_trip_updates()

    if realtime_df.empty:
        st.warning("No real-time vehicle data available.")
    
    if trip_updates_df.empty:
        st.warning("No trip updates available.")

# Initialize Map
m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="cartodb positron")

# Display vehicle counts
if not realtime_df.empty:
    st.sidebar.write(f"Active vehicles: {len(realtime_df)}")

# Highlight Selected Route
if selected_route != "None" and not static_stops.empty and not realtime_df.empty:
    filtered_stops = static_stops[static_stops["route_short_name"] == selected_route]
    
    if not filtered_stops.empty:
        # Extract route_id for the selected route
        route_ids = filtered_stops["route_id"].unique().tolist()
        
        # Create stops markers
        for _, row in filtered_stops.iterrows():
            try:
                folium.Marker(
                    location=[float(row["stop_lat"]), float(row["stop_lon"])],
                    popup=f"Stop: {row['stop_name']} (ID: {row['stop_id']})",
                    icon=folium.Icon(color="blue", icon="bus", prefix="fa"),
                ).add_to(m)
            except (ValueError, TypeError) as e:
                continue

        # Filter real-time vehicles for the selected route
        realtime_filtered = realtime_df[realtime_df["route_id"].isin(route_ids)]
        
        if not realtime_filtered.empty:
            st.sidebar.write(f"Vehicles on route {selected_route}: {len(realtime_filtered)}")
            
            # Add vehicle markers
            for _, row in realtime_filtered.iterrows():
                try:
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        popup=f"Vehicle: {row['vehicle_id']}<br>Speed: {row.get('speed', 'N/A')} km/h",
                        icon=folium.Icon(color="red", icon="bus", prefix="fa"),
                    ).add_to(m)
                except (ValueError, TypeError) as e:
                    continue
        else:
            st.warning(f"No real-time vehicle data available for route {selected_route}.")
    else:
        st.warning(f"No stop data found for route {selected_route}.")

# Display Map
st.subheader("🗺️ Live Map")
folium_static(m)

# Display Trip Updates
st.subheader("🚦 Trip Updates & Delays")
if not trip_updates_df.empty:
    # Filter trip updates for the selected route if a route is selected
    if selected_route != "None":
        route_ids = static_stops[static_stops["route_short_name"] == selected_route]["route_id"].unique().tolist()
        filtered_updates = trip_updates_df[trip_updates_df["route_id"].isin(route_ids)]
        
        if not filtered_updates.empty:
            st.dataframe(filtered_updates)
        else:
            st.info(f"No trip updates available for route {selected_route}.")
    else:
        # Display all trip updates
        st.dataframe(trip_updates_df)
else:
    st.info("No trip updates available.")

# Auto-refresh using Streamlit's rerun functionality
if auto_refresh:
    st.sidebar.write("Next refresh in 30 seconds...")
    time_placeholder = st.sidebar.empty()
    
    # Create a countdown timer
    if "counter" not in st.session_state:
        st.session_state.counter = 30
    
    if st.session_state.counter <= 0:
        st.session_state.counter = 30
        st.experimental_rerun()
    else:
        st.session_state.counter -= 1
        time_placeholder.write(f"Refreshing in {st.session_state.counter} seconds...")
        time.sleep(1)
        st.experimental_rerun()
