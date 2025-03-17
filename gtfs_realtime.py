import requests
from google.transit import gtfs_realtime_pb2

# GTFS-RT URL (TransLink - South East Queensland)
GTFS_RT_VEHICLE_POSITIONS_URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/VehiclePositions/Bus"

def get_vehicle_positions(route_id=None):
    """Fetch and parse GTFS-RT vehicle positions from TransLink API."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return {"error": "Failed to fetch real-time data"}

    feed.ParseFromString(response.content)

    vehicles = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            vehicle = entity.vehicle
            if route_id and vehicle.trip.route_id != route_id:
                continue  # Filter by route

            vehicles.append({
                "vehicle_id": vehicle.vehicle.id,
                "route_id": vehicle.trip.route_id,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "speed": vehicle.position.speed if vehicle.position.HasField("speed") else None
            })

    return vehicles

def list_vehicles():
    """Fetch and list all active vehicles."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(GTFS_RT_VEHICLE_POSITIONS_URL)

    if response.status_code != 200:
        return []

    feed.ParseFromString(response.content)

    return [{"vehicle_id": entity.vehicle.vehicle.id, "route_id": entity.vehicle.trip.route_id}
            for entity in feed.entity if entity.HasField("vehicle")]
