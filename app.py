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
from gtfs_realtime import get_vehicle_updates 
from gtfs_static import load_gtfs_data 

# Load GTFS static data
routes_df, stops_df, trips_df, stop_times_df, shapes_df = load_gtfs_data()

# Fetch vehicle data
vehicles_df = get_vehicle_updates()


def get_route_shapes(route_id, direction, trips_df, shapes_df):
    """Retrieve and structure shape points for a given route ID and direction."""
    trip_shapes = trips_df[(trips_df["route_id"] == route_id) & (trips_df["direction_id"] == str(direction))][["shape_id"]].drop_duplicates()
    shape_ids = trip_shapes["shape_id"].unique()

    if len(shape_ids) == 0:
        return pd.DataFrame()

    route_shapes = shapes_df[shapes_df["shape_id"].isin(shape_ids)]
    
    # Convert data types
    route_shapes["shape_pt_lat"] = route_shapes["shape_pt_lat"].astype(float)
    route_shapes["shape_pt_lon"] = route_shapes["shape_pt_lon"].astype(float)
    route_shapes["shape_pt_sequence"] = route_shapes["shape_pt_sequence"].astype(int)

    # Sort by shape_id and sequence
    route_shapes = route_shapes.sort_values(by=["shape_id", "shape_pt_sequence"])

    # Process each shape_id separately
    line_segments = []
    
    for shape_id in shape_ids:
        shape_points = route_shapes[route_shapes["shape_id"] == shape_id].copy()
        
        # Create start-end coordinate pairs for folium
        shape_points["next_lat"] = shape_points["shape_pt_lat"].shift(-1)
        shape_points["next_lon"] = shape_points["shape_pt_lon"].shift(-1)
        
        # Remove last row (no next point to connect)
        shape_points = shape_points.dropna(subset=["next_lat", "next_lon"])
        
        line_segments.append(shape_points)
    
    if not line_segments:
        return pd.DataFrame()
        
    # Combine all line segments
    return pd.concat(line_segments, ignore_index=True)

def plot_map(vehicles_df, route_shapes=None, route_stops=None):
    """Plot real-time vehicles and optionally route path on a map."""
    # Default center for SEQ area if no vehicles data
    if vehicles_df.empty:
        map_center = [-27.5, 153.0]
    else:
        map_center = [vehicles_df["lat"].mean(), vehicles_df["lon"].mean()]
    
    m = folium.Map(location=map_center, zoom_start=12)
    
    # Add vehicles as markers
    for _, row in vehicles_df.iterrows():
        color = "green" if row["status"] == "On Time" else "orange" if row["status"] == "Delayed" else "red"
        
        folium.Marker(
            location=[row["lat"], row["lon"]],
            icon=folium.Icon(color=color, icon="bus", prefix="fa"),
            popup=f"Vehicle {row['vehicle_id']} on Route {row['route_id']}"
        ).add_to(m)

        folium.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.DivIcon(html=f'<div style="font-size: 12px; font-weight: bold; color: black; text-align: center;">{row["vehicle_id"]}-{f"At stop:{row['Stop Sequence']}"}</div>')
            ).add_to(m)
    
    # Add route shapes as polylines
    if route_shapes is not None and not route_shapes.empty:
        # Group by shape_id to create continuous lines
        for shape_id, group in route_shapes.groupby("shape_id"):
            # Create a list of coordinates for each shape
            coordinates = []
            for _, point in group.iterrows():
                coordinates.append([point["shape_pt_lat"], point["shape_pt_lon"]])
            
            # Add the polyline for this shape
            if coordinates:
                folium.PolyLine(
                    locations=coordinates,
                    color="red",
                    weight=3,
                    tooltip=f"Shape {shape_id}"
                ).add_to(m)
    
    # Display map
    folium_static(m)

# Streamlit App
st.set_page_config(layout="wide")
st.title("GTFS Realtime Vehicle Fields")

# Cache the last selection
if "selected_region" not in st.session_state:
    st.session_state.selected_region = "Gold Coast"
if "selected_route" not in st.session_state:
    st.session_state.selected_route = "777"
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = "N/A"
if "next_refresh" not in st.session_state:
    st.session_state["next_refresh"] = "N/A"

# Sidebar filters
st.sidebar.title("🚍 Select Filters")

# Region selection
region_options = sorted(vehicles_df["region"].unique())
st.session_state.selected_region = st.sidebar.selectbox("Select a Region", region_options, index=region_options.index(st.session_state.selected_region) if st.session_state.selected_region in region_options else 0)

# Filter routes based on selected region
filtered_df = vehicles_df[vehicles_df["region"] == st.session_state.selected_region]
route_options = ["All Routes"] + sorted(filtered_df["route_name"].unique())
st.session_state.selected_route = st.sidebar.selectbox(
    "Select a Route", 
    route_options, 
    index=route_options.index(st.session_state.selected_route) if st.session_state.selected_route in route_options else 0
)

# Apply filters
if st.session_state.selected_route == "All Routes":
    display_df = filtered_df  # Show all vehicles in the region
    
    # Show status filter only when "All Routes" is selected
    status_options = ["All Statuses"] + sorted(display_df["status"].unique())
    selected_status = st.sidebar.selectbox("Select Status", status_options, index=0)
    
    # Filter by status if a specific status is selected
    if selected_status != "All Statuses":
        display_df = display_df[display_df["status"] == selected_status]
    
    # Plot map with all filtered vehicles
    plot_map(display_df)
else:
    # Get the route_id for the selected route name
    route_id = filtered_df[filtered_df["route_name"] == st.session_state.selected_route]["route_id"].iloc[0]
    
    # Filter vehicles to show only selected route
    filtered_vehicles = filtered_df[filtered_df["route_id"] == route_id]
    
    if filtered_vehicles.empty:
        st.warning(f"No vehicles currently active on route {st.session_state.selected_route}")
        plot_map(filtered_vehicles)
    else:
        # Get available directions for this route
        directions = trips_df[trips_df["route_id"] == route_id]["direction_id"].unique()
        
        if len(directions) > 0:
            selected_direction = st.sidebar.radio(
                "Select Direction",
                options=directions,
                format_func=lambda d: "Outbound" if d == "0" else "Inbound"
            )
            
            # Filter vehicles by selected direction
            trips_on_selected_direction = trips_df[(trips_df["route_id"] == route_id) & 
                                                 (trips_df["direction_id"] == selected_direction)]["trip_id"].unique()
            
            # Filter vehicles that are on trips with the selected direction
            filtered_vehicles_by_direction = filtered_vehicles[filtered_vehicles["trip_id"].isin(trips_on_selected_direction)]
            
            # Add color coding to vehicles based on status
            filtered_vehicles_by_direction = filtered_vehicles_by_direction.copy()
            filtered_vehicles_by_direction["color"] = filtered_vehicles_by_direction["status"].apply(
                lambda status: "green" if status == "On Time" else "orange" if status == "Delayed" else "red"
            )
            
            # Get shapes for this route and direction
            route_shapes = get_route_shapes(route_id, selected_direction, trips_df, shapes_df)
            
            # Plot map with filtered vehicles and route
            plot_map(filtered_vehicles_by_direction, route_shapes)
        else:
            st.warning(f"No direction information available for route {st.session_state.selected_route}")
            # Add color coding for this case as well
            filtered_vehicles = filtered_vehicles.copy()
            filtered_vehicles["color"] = filtered_vehicles["status"].apply(
                lambda status: "green" if status == "On Time" else "orange" if status == "Delayed" else "red"
            )
            plot_map(filtered_vehicles)

