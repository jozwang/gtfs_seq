import pandas as pd
import requests
import zipfile
import io

# GTFS Static Data URL
GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"

def download_gtfs():
    """Download GTFS ZIP file and return as an in-memory object."""
    response = requests.get(GTFS_ZIP_URL)
    if response.status_code == 200:
        return zipfile.ZipFile(io.BytesIO(response.content))
    else:
        raise Exception("Failed to download GTFS data.")

def list_gtfs_files(zip_obj):
    """List all files in the GTFS ZIP archive."""
    return zip_obj.namelist()

def extract_file(zip_obj, filename):
    """Extract a file from a GTFS ZIP archive and return as a DataFrame."""
    with zip_obj.open(filename) as file:
        return pd.read_csv(file, dtype=str, low_memory=False)

def load_static_gtfs():
    """Load static GTFS data and return scheduled stops and routes."""
    zip_obj = download_gtfs()
    file_list = list_gtfs_files(zip_obj)
    
    # Display list of available GTFS files in Streamlit
    st.sidebar.write("### Available GTFS Files:")
    st.sidebar.write(file_list)
    
    # Extract necessary files if they exist
    routes_df = extract_file(zip_obj, "routes.txt") if "routes.txt" in file_list else pd.DataFrame()
    stops_df = extract_file(zip_obj, "stops.txt") if "stops.txt" in file_list else pd.DataFrame()
    trips_df = extract_file(zip_obj, "trips.txt") if "trips.txt" in file_list else pd.DataFrame()
    stop_times_df = extract_file(zip_obj, "stop_times.txt") if "stop_times.txt" in file_list else pd.DataFrame()

    if not stop_times_df.empty and not trips_df.empty and not routes_df.empty and not stops_df.empty:
        # Merge stop times with trip details
        enriched_stops = stop_times_df.merge(trips_df, on="trip_id", how="left")
        enriched_stops = enriched_stops.merge(routes_df, on="route_id", how="left")
        stops_data = enriched_stops.merge(stops_df, on="stop_id", how="left",  indicator=True)

        # Convert arrival times to datetime
        stops_data["arrival_time"] = pd.to_datetime(enriched_stops["arrival_time"], format="%H:%M:%S", errors="coerce")
    else:
        stops_data = pd.DataFrame()

    return stops_data 

