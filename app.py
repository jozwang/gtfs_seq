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
        folium.Marker(
            location=[row["lat"], row["lon"]],
            icon=folium.Icon(color="blue", icon="bus", prefix="fa"),
            popup=f"Vehicle {row['vehicle_id']} on Route {row['route_id']}"
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

# Streamlit UI
st.title("SEQ Public Transport Real-Time on a Map")

if not vehicles_df.empty:
    route_options = ["All Routes"] + sorted(vehicles_df["route_id"].unique())
    selected_route = st.selectbox("Select a Route", route_options)
    
    if selected_route != "All Routes" and trips_df is not None:
        # Filter vehicles to show only selected route
        filtered_vehicles = vehicles_df[vehicles_df["route_id"] == selected_route]
        
        if filtered_vehicles.empty:
            st.warning(f"No vehicles currently active on route {selected_route}")
            plot_map(filtered_vehicles)
        else:
            # Get available directions for this route
            directions = trips_df[trips_df["route_id"] == selected_route]["direction_id"].unique()
            
            if len(directions) > 0:
                selected_direction = st.radio(
                    "Select Direction", 
                    options=directions, 
                    format_func=lambda d: "Outbound" if d == "0" else "Inbound"
                )
                
                # Get shapes for this route and direction
                route_shapes = get_route_shapes(selected_route, selected_direction, trips_df, shapes_df)
                
                # Plot map with vehicles and route
                plot_map(filtered_vehicles, route_shapes)
            else:
                st.warning(f"No direction information available for route {selected_route}")
                plot_map(filtered_vehicles)
    else:
        # Show all vehicles without route shapes
        plot_map(vehicles_df)
else:
    st.error("No real-time vehicle data available")
