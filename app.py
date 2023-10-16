import streamlit as st
import pandas as pd
import numpy as np
import h3
import googlemaps
import pydeck as pdk
from datetime import datetime

def h3_to_address(h3_code, gmaps):
    """Convert H3 code to a recognizable address using Google Maps API."""
    # Convert H3 code to center latitude and longitude
    lat, lon = h3.h3_to_geo(h3_code)
    
    # Use Google Maps Reverse Geocoding API
    result = gmaps.reverse_geocode((lat, lon))
    
    # Extract the address or neighborhood name
    if result and 'formatted_address' in result[0]:
        return result[0]['formatted_address']
    else:
        return "Unknown Location"

def spatid_v3(df, lat_col, lon_col, time_col, date_col, time_bin, spatial_resolution, threshold=None):
    """Modified SpatioTemporal Influx Detection function to aggregate raw rows for each alarm."""
    df = df.dropna(subset=[lat_col, lon_col, time_col, date_col]).copy()
    
    df["hex_id"] = df.apply(lambda row: h3.geo_to_h3(row[lat_col], row[lon_col], spatial_resolution), axis=1)
    
    df['time'] = df[time_col].apply(lambda x: datetime.strptime(x, '%H:%M:%S').time())
    df['total_minutes'] = df['time'].apply(lambda x: x.hour*60 + x.minute)
    df['bin'] = np.ceil(df['total_minutes'] / time_bin).astype(int)
    
    # Aggregate raw rows for each group
    aggregated_data = df.groupby([date_col, 'hex_id', 'bin']).apply(lambda group: group.to_dict(orient='records')).reset_index(name='raw_rows')
    incident_counts = df.groupby([date_col, 'hex_id', 'bin']).size().reset_index(name='Incident_count')
    
    grouped_data = pd.merge(aggregated_data, incident_counts, on=[date_col, 'hex_id', 'bin'])
    
    if threshold is None:
        threshold_data = grouped_data.groupby('hex_id')['Incident_count'].quantile(0.95).reset_index(name='Threshold')
        grouped_data = pd.merge(grouped_data, threshold_data, on='hex_id')
        threshold = grouped_data['Threshold']
    else:
        grouped_data['Threshold'] = threshold
    
    influx_events = grouped_data[grouped_data['Incident_count'] >= threshold]
    
    return influx_events

# Functions for SpatioTemporal Influx Detection (from previous discussions)
# [Include the spatid_v3 and h3_to_address functions here]

# Streamlit App
st.title('SpatioTemporal Influx Detection (Spa.T.I.D)')

# Upload CSV file
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, low_memory=False)
    st.write("Uploaded Data Overview:")
    st.write(df.head())

    # User Inputs
    lat_col = st.text_input("Latitude Column Name:", value="Latitude")
    lon_col = st.text_input("Longitude Column Name:", value="Longitude")
    date_col = st.text_input("Date Column Name:", value="Date")
    time_col = st.text_input("Time Column Name (Leave empty if not applicable):", value="Time")
    spatial_resolution = st.slider("Choose H3 Spatial Resolution (0-15):", 0, 15, 7)
    time_bin = st.slider("Choose Temporal Window (in minutes):", 15, 180, 60)

...

if st.button('Process Data'):
    # Fetch influx events
    influx_events = spatid_v3(df, lat_col, lon_col, time_col, date_col, time_bin, spatial_resolution)

    # Initialize Google Maps API
    gmaps = googlemaps.Client(key='AIzaSyBIn9U1eB5eYb8fD9N3hR-2Rhm8yP2G5Pk')

    # Get address for each H3 code
    influx_events["address"] = influx_events["hex_id"].apply(lambda x: h3_to_address(x, gmaps))

    # Convert H3 codes to latitude and longitude for mapping
    influx_events["lat"], influx_events["lon"] = zip(*influx_events["hex_id"].apply(h3.h3_to_geo))
    
    # Create a copy of influx_events without the 'raw_rows' column for mapping
    map_data = influx_events.drop(columns=['raw_rows'])

...

    # Display results on map
    view_state = pdk.ViewState(
    latitude=influx_events["lat"].mean(),
    longitude=influx_events["lon"].mean(),
    zoom=10
    )
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,  # Use DataFrame directly
        get_position=["lon", "lat"],
        get_radius=500,  # Adjust based on the desired appearance
        get_fill_color="[255, 0, 0, 180]",  # Semi-transparent
        get_line_color="[0, 0, 0]",
        stroked=True,
        pickable=True
    )
    
    tooltip = {
        "html": "<b>Address:</b> {address}<br/><b>Incident Count:</b> {Incident_count}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
    
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
    
    # Display the combination of space and time windows that generated the alert
    alert_table = influx_events[['hex_id', 'address', date_col, 'bin', 'Incident_count']]
    st.write("Space and Time Windows that generated alerts:")
    st.write(alert_table)
