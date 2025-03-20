import requests
import pandas as pd
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
    
    feed.ParseFromString(content)
    vehicles = []
    # timestamp = datetime.utcnow()
    
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            vehicles.append({
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "vehicle_id": vehicle.vehicle.label,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "Stop Sequence": vehicle.current_stop_sequence ,
                "Stop ID": vehicle.stop_id ,
                "current_status": vehicle.current_status ,
                "Timestamp": vehicle.timestamp if vehicle.HasField("timestamp") else "Unknown"
            })
    
    return pd.DataFrame(vehicles)

def get_trip_updates():
    """Fetch trip updates (delays, cancellations) from GTFS-RT API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    content = fetch_gtfs_rt("https://gtfsrt.api.translink.com.au/api/realtime/SEQ/TripUpdates/Bus")
    if not content:
        return pd.DataFrame()
    
    feed.ParseFromString(content)
    updates = []
    
    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip_update = entity.trip_update
            delay = trip_update.stop_time_update[0].arrival.delay if trip_update.stop_time_update else None
            updates.append({
                "trip_id": trip_update.trip.trip_id,
                "route_id": trip_update.trip.route_id,
                "delay": delay,
                "status": "Delayed" if delay and delay > 300 else "On Time"
            })
    
    return pd.DataFrame(updates)

def get_vehicle_updates():
    """Merge real-time vehicle positions with trip updates on trip_id and route_id."""
    vehicles_df = get_realtime_vehicles()
    updates_df = get_trip_updates()
    
    if vehicles_df.empty:
        return updates_df
    if updates_df.empty:
        return vehicles_df
    
    veh_update = vehicles_df.merge(updates_df, on=["trip_id", "route_id"], how="left")
    return veh_update
