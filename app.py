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
import gtfs_reatime
import gtfs_static

routes_df, stops_df, trips_df, stop_times_df, shapes_df = load_gtfs_data()
# Fetch vehicle data
vehicles_df = get_vehicle_updates()

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
st.title("SEQ Public Transport Real-Time on a Map")



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
