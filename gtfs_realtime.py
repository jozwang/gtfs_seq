import requests
import pandas as pd
import streamlit as st
from google.transit import gtfs_realtime_pb2
from datetime import datetime

def fetch_gtfs_rt(url):
    """Fetch GTFS-RT data from a given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        st.error(f"Error fetching GTFS-RT data: {e}")
        return None

def get_realtime_vehicles():
    """Fetch real-time vehicle positions from GTFS-RT API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    content = fetch_gtfs_rt("https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus")
    if not content:
        return pd.DataFrame()
    
    try:
        feed.ParseFromString(content)
        vehicles = []
        
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                vehicle = entity.vehicle
                vehicle_data = {
                    "trip_id": vehicle.trip.trip_id if vehicle.HasField("trip") else "",
                    "route_id": vehicle.trip.route_id if vehicle.HasField("trip") else "",
                    "vehicle_id": vehicle.vehicle.id if vehicle.HasField("vehicle") else "",
                    "lat": vehicle.position.latitude if vehicle.HasField("position") else 0,
                    "lon": vehicle.position.longitude if vehicle.HasField("position") else 0,
                    "speed": round(vehicle.position.speed * 3.6, 1) if vehicle.HasField("position") and vehicle.position.HasField("speed") else 0,
                    "realtime_timestamp": vehicle.timestamp if vehicle.HasField("timestamp") else 0
                }
                vehicles.append(vehicle_data)
        
        return pd.DataFrame(vehicles)
    except Exception as e:
        st.error(f"Error parsing vehicle positions: {e}")
        return pd.DataFrame()

def get_trip_updates():
    """Fetch trip updates (delays, cancellations) from GTFS-RT API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    content = fetch_gtfs_rt("https://gtfsrt.api.translink.com.au/api/realtime/SEQ/TripUpdates/Bus")
    if not content:
        return pd.DataFrame()
    
    try:
        feed.ParseFromString(content)
        updates = []
        
        for entity in feed.entity:
            if entity.HasField("trip_update"):
                trip_update = entity.trip_update
                delay = None
                
                if len(trip_update.stop_time_update) > 0:
                    stu = trip_update.stop_time_update[0]
                    if stu.HasField("arrival") and stu.arrival.HasField("delay"):
                        delay = stu.arrival.delay
                
                updates.append({
                    "trip_id": trip_update.trip.trip_id,
                    "route_id": trip_update.trip.route_id,
                    "delay": delay if delay is not None else 0,
                    "delay_minutes": round(delay/60, 1) if delay is not None else 0,
                    "status": "Delayed" if delay and delay > 180 else "On Time"
                })
        
        return pd.DataFrame(updates)
    except Exception as e:
        st.error(f"Error parsing trip updates: {e}")
        return pd.DataFrame()
