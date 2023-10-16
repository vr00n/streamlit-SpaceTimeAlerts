import streamlit as st
import pandas as pd
import numpy as np
import h3
import googlemaps
import pydeck as pdk
from datetime import datetime

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

    if st.button('Process Data'):
        # Fetch influx events
        influx_events = spatid_v3(df, lat_col, lon_col, time_col, date_col, time_bin, spatial_resolution)

        # Initialize Google Maps API
        gmaps = googlemaps.Client(key='YOUR_GOOGLE_MAPS_API_KEY')

        # Get address for each H3 code
        influx_events["address"] = influx_events["hex_id"].apply(lambda x: h3_to_address(x, gmaps))

        # Convert H3 codes to latitude and longitude for mapping
        influx_events["lat"], influx_events["lon"] = zip(*influx_events["hex_id"].apply(h3.h3_to_geo))
        
        # Display results on map
        view_state = pdk.ViewState(
            latitude=influx_events["lat"].mean(),
            longitude=influx_events["lon"].mean(),
            zoom=10
        )
        layer = pdk.Layer(
            "HexagonLayer",
            data=influx_events,
            get_hexagon="hex_id",
            get_position=["lon", "lat"],
            get_fill_color="[255, 0, 0]",
            get_line_color="[0, 0, 0]",
            filled=True,
            stroked=True,
            extruded=True,
            pickable=True
        )
        tooltip = {
            "html": "<b>Address:</b> {address}<br/><b>Incident Count:</b> {Incident_count}",
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

# Reminder: Replace 'YOUR_GOOGLE_MAPS_API_KEY' with your actual Google Maps API key.
