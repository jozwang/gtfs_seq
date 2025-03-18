import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
from datetime import datetime

# GTFS-RT URL (TransLink - Bus)
GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"
GTFS_RT_TRIP_UPDATES_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/TripUpdates/Bus"

def get_realtime_vehicles():
    """Fetch real-time vehicle positions from GTFS-RT API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return pd.DataFrame(), "Failed to fetch real-time data"

    feed.ParseFromString(response.content)
    vehicles = []
    timestamp = datetime.utcnow()

    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            vehicles.append({
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "vehicle_id": vehicle.vehicle.id,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "Stop Sequence": vehicle.current_stop_sequence if vehicle.HasField("current_stop_sequence") else "Unknown",
                "Stop ID": vehicle.stop_id if vehicle.HasField("stop_id") else "Unknown",
                "Current Status": vehicle.current_status if vehicle.HasField("current_status") else "Unknown",
                "realtime_timestamp": timestamp
            })

    return pd.DataFrame(vehicles), None

def get_trip_updates():
    """Fetch trip updates (delays, cancellations) from GTFS-RT API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_TRIP_UPDATES_URL)

    if response.status_code != 200:
        return pd.DataFrame(), "Failed to fetch trip updates"

    feed.ParseFromString(response.content)
    updates = []

    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip_update = entity.trip_update
            delay = trip_update.stop_time_update[0].arrival.delay if trip_update.stop_time_update else None
            updates.append({
                "trip_id": trip_update.trip.trip_id,
                "route_id": trip_update.trip.route_id,
                "delay": delay,
                "status": "Delayed" if delay and delay > 0 else "On Time"
            })

    return pd.DataFrame(updates), None
