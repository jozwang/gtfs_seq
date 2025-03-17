import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from gtfs_static import get_route_shape, list_routes
from gtfs_realtime import get_vehicle_positions

# Streamlit Layout
st.set_page_config(layout="wide")

st.title("🚍 Real-time TransLink GTFS Map")

# Load routes from static GTFS
routes = list_routes()

# Route selection
route_dict = {route["route_name"]: route["route_id"] for route in routes}
selected_route_name = st.sidebar.selectbox("Select a Route", options=["None"] + list(route_dict.keys()))
selected_route = route_dict.get(selected_route_name, None)

# Fetch GTFS-RT data
vehicle_data = get_vehicle_positions()

# Filter real-time data for the selected route
filtered_rt_data = vehicle_data[vehicle_data["route_id"] == selected_route] if selected_route else vehicle_data

# Initialize map (2/3 left side)
map_column, table_column = st.columns([2, 1])

with map_column:
    m = folium.Map(location=[-27.4698, 153.0251], zoom_start=12, tiles="CartoDB positron")

    # Highlight selected route
    if selected_route:
        shape = get_route_shape(selected_route)
        if shape:
            folium.PolyLine(locations=[(lat, lon) for lon, lat in shape.coords], color="blue", weight=4).add_to(m)

    # Add Real-time Vehicles
    for _, vehicle in filtered_rt_data.iterrows():
        folium.Marker(
            location=[vehicle["lat"], vehicle["lon"]],
            popup=f"Vehicle ID: {vehicle['vehicle_id']}<br>Speed: {vehicle['speed']} km/h",
            icon=folium.Icon(color="red"),
        ).add_to(m)

    folium_static(m)

# Display Table (1/3 right side)
with table_column:
    if selected_route:
        st.write(f"### Route Data for {selected_route_name}")
        static_data = pd.DataFrame([{"route_id": selected_route, "route_name": selected_route_name}])
        combined_data = pd.concat([static_data, filtered_rt_data], axis=1)
    else:
        st.write("### All Real-time Vehicles")
        combined_data = filtered_rt_data

    st.dataframe(combined_data)
