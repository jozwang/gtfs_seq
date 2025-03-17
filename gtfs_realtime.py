import requests
from google.transit import gtfs_realtime_pb2
import pandas as pd

GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"

def get_vehicle_positions():
    """Fetch real-time GTFS-RT vehicle positions from TransLink API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return []

    feed.ParseFromString(response.content)

    vehicles = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            vehicles.append({
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "speed": vehicle.position.speed if vehicle.position.HasField("speed") else None,
                "vehicle_id": vehicle.vehicle.id
            })

    return pd.DataFrame(vehicles)
