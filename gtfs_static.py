import pandas as pd
import requests
import zipfile
import io
from shapely.geometry import LineString

# GTFS Static Data URL
GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"

def download_gtfs():
    """Download GTFS ZIP file and return as an in-memory object."""
    response = requests.get(GTFS_ZIP_URL)
    if response.status_code == 200:
        return zipfile.ZipFile(io.BytesIO(response.content))
    else:
        raise Exception("Failed to download GTFS data.")

def extract_file(zip_obj, filename):
    """Extract a file from a GTFS ZIP archive and return as a DataFrame."""
    with zip_obj.open(filename) as file:
        return pd.read_csv(file)

def load_static_gtfs():
    """Load static GTFS data and return scheduled stops, routes, and shapes."""
    zip_obj = download_gtfs()

    # Extract necessary files
    routes_df = extract_file(zip_obj, "routes.txt")
    shapes_df = extract_file(zip_obj, "shapes.txt")
    trips_df = extract_file(zip_obj, "trips.txt")
    stop_times_df = extract_file(zip_obj, "stop_times.txt")

    # Merge stop times with trip details
    enriched_stops = stop_times_df.merge(trips_df, on="trip_id", how="left")
    enriched_stops = enriched_stops.merge(routes_df, on="route_id", how="left")

    # Convert arrival times to datetime
    enriched_stops["arrival_time"] = pd.to_datetime(enriched_stops["arrival_time"], format="%H:%M:%S", errors="coerce")

    return enriched_stops, shapes_df
