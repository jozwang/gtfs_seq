import streamlit as st
import folium
from streamlit_folium import folium_static
from gtfs_realtime import get_vehicle_positions, list_vehicles
from gtfs_static import get_route_shape, list_routes

# Streamlit UI
st.title("🚍 Real-time GTFS Map")

# Load route and vehicle lists
routes = list_routes()
vehicles = list_vehicles()

# Route selection
route_ids = {route["route_name"]: route["route_id"] for route in routes}
selected_route = st.selectbox("Select a Route", options=["None"] + list(route_ids.keys()))

# Vehicle selection
vehicle_ids = {vehicle["vehicle_id"]: vehicle["route_id"] for vehicle in vehicles}
selected_vehicle = st.selectbox("Select a Vehicle", options=["None"] + list(vehicle_ids.keys()))

# Initialize map
m = folium.Map(location=[-33.8688, 151.2093], zoom_start=12)

# Display Route Path
if selected_route != "None":
    shape = get_route_shape(route_ids[selected_route])
    if shape:
        folium.PolyLine(locations=[(lat, lon) for lon, lat in shape.coords], color="blue", weight=4).add_to(m)

# Display Vehicles
vehicle_data = get_vehicle_positions(route_ids[selected_route] if selected_route != "None" else None)

for vehicle in vehicle_data:
    if selected_vehicle == "None" or vehicle["vehicle_id"] == selected_vehicle:
        folium.Marker(
            location=[vehicle["lat"], vehicle["lon"]],
            popup=f"Vehicle ID: {vehicle['vehicle_id']}<br>Speed: {vehicle['speed']} km/h",
            icon=folium.Icon(color="red" if vehicle["vehicle_id"] == selected_vehicle else "green"),
        ).add_to(m)

# Display map
folium_static(m)
