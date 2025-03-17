import pandas as pd
import requests
import zipfile
import os
import io
from shapely.geometry import LineString

GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"
GTFS_CACHE_PATH = "gtfs_cache.zip"

def download_gtfs():
    """Download GTFS ZIP if not cached."""
    if not os.path.exists(GTFS_CACHE_PATH):
        print("Downloading GTFS data...")
        response = requests.get(GTFS_ZIP_URL, stream=True)
        if response.status_code == 200:
            with open(GTFS_CACHE_PATH, "wb") as f:
                f.write(response.content)
            print("GTFS data downloaded successfully.")
        else:
            print("Failed to download GTFS data.")

def extract_file_from_zip(filename):
    """Extract a specific file from the GTFS ZIP archive."""
    with zipfile.ZipFile(GTFS_CACHE_PATH, "r") as zip_ref:
        with zip_ref.open(filename) as file:
            return pd.read_csv(file)

def get_route_shape(route_id):
    """Extract and return route shape data as LineString."""
    download_gtfs()
    shapes_df = extract_file_from_zip("shapes.txt")

    route_shapes = shapes_df[shapes_df["shape_id"].str.contains(route_id, na=False)]
    if route_shapes.empty:
        return None

    return LineString(zip(route_shapes["shape_pt_lon"], route_shapes["shape_pt_lat"]))

def list_routes():
    """Extract and list available routes from GTFS data."""
    download_gtfs()
    routes_df = extract_file_from_zip("routes.txt")
    return [{"route_id": row["route_id"], "route_name": row["route_short_name"]} for _, row in routes_df.iterrows()]
