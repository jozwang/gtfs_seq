import pandas as pd
import requests
import zipfile
import io
import streamlit as st

# GTFS Static Data URL
GTFS_ZIP_URL = "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink/resource/e43b6b9f-fc2b-4630-a7c9-86dd5483552b/download"

def download_gtfs():
    """Download GTFS ZIP file and return as an in-memory object."""
    try:
        response = requests.get(GTFS_ZIP_URL, timeout=10)
        response.raise_for_status()
        return zipfile.ZipFile(io.BytesIO(response.content))
    except requests.RequestException as e:
        st.error(f"Error downloading GTFS data: {e}")
        return None
    except zipfile.BadZipFile as e:
        st.error(f"Invalid ZIP file: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None

def list_gtfs_files(zip_obj):
    """List all files in the GTFS ZIP archive."""
    if not zip_obj:
        return []
    try:
        return zip_obj.namelist()
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return []

def extract_file(zip_obj, filename):
    """Extract a file from a GTFS ZIP archive and return as a DataFrame."""
    if not zip_obj:
        return pd.DataFrame()
    
    try:
        with zip_obj.open(filename) as file:
            return pd.read_csv(file, dtype=str, low_memory=False)
    except KeyError:
        st.warning(f"File not found in archive: {filename}")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Could not read {filename}: {e}")
        return pd.DataFrame()

def load_static_gtfs():
    """Load static GTFS data and return stops and routes."""
    try:
        zip_obj = download_gtfs()
        if not zip_obj:
            st.error("Failed to download GTFS data.")
            return pd.DataFrame()
        
        file_list = list_gtfs_files(zip_obj)
        
        # Extract necessary files
        routes_df = extract_file(zip_obj, "routes.txt")
        stops_df = extract_file(zip_obj, "stops.txt")
        trips_df = extract_file(zip_obj, "trips.txt")
        stop_times_df = extract_file(zip_obj, "stop_times.txt")
        
        if routes_df.empty:
            st.error("Failed to extract routes data.")
            return pd.DataFrame()
        if stops_df.empty:
            st.error("Failed to extract stops data.")
            return pd.DataFrame()
        if trips_df.empty:
            st.error("Failed to extract trips data.")
            return pd.DataFrame()
        if stop_times_df.empty:
            st.error("Failed to extract stop times data.")
            return pd.DataFrame()

        # Merge data
        stops_data = stop_times_df.merge(trips_df, on="trip_id", how="left")
        stops_data = stops_data.merge(routes_df, on="route_id", how="left")
        stops_data = stops_data.merge(stops_df, on="stop_id", how="left")
        
        # Skip datetime conversion as it's not necessary for basic functionality
        # and can be problematic with times past midnight
        
        return stops_data
    except Exception as e:
        st.error(f"Error loading static GTFS data: {e}")
        return pd.DataFrame()
