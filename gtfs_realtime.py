import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
from datetime import datetime

# GTFS-RT URL (TransLink - Bus)
GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"

def get_realtime_data():
    """Fetch real-time GTFS-RT data and return a DataFrame with timestamps."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return pd.DataFrame(), "Failed to fetch real-time data"

    feed.ParseFromString(response.content)

    vehicles = []
    timestamp = datetime.utcnow()  # Capture the real-time timestamp

        for entity in feed.entity:
            if entity.HasField("vehicle"):
                vehicle = entity.vehicle
                trip = vehicle.trip
                position = vehicle.position                


                data.append({
                    "Vehicle ID": vehicle.vehicle.id,
                    "Label": vehicle.vehicle.label,
                    "Latitude": vehicle.position.latitude,
                    "Longitude": vehicle.position.longitude,
                    "Route ID": trip.route_id ,
                    "Trip ID": trip.trip_id ,
                    "Stop Sequence": vehicle.current_stop_sequence ,
                    "Stop ID": vehicle.stop_id ,
                    "current_status": vehicle.current_status ,
                    "Timestamp": vehicle.timestamp if vehicle.HasField("timestamp") else "Unknown"
                })

    return pd.DataFrame(vehicles), None

def calculate_arrival_delays(static_stops, realtime_data):
    """Calculate the difference between scheduled and real-time arrivals."""
    # Merge static stops with real-time data on trip_id
    merged_df = pd.merge(static_stops, realtime_data, on="trip_id", how="inner")

    # Compute time difference
    merged_df["arrival_delay"] = (merged_df["realtime_timestamp"] - merged_df["arrival_time"]).dt.total_seconds() / 60  # in minutes

    return merged_df
