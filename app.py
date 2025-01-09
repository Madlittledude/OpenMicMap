import streamlit as st
import pandas as pd
import json
import googlemaps
import pydeck as pdk
import os

# Load API key and JSON data
API_KEY = st.secrets["API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)

with open("data.json", "r") as file:
    data = json.load(file)

# Function to get latitude and longitude using Google Maps API
@st.cache_data
def geocode_address(address):
    try:
        result = gmaps.geocode(address)
        if result:
            location = result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except Exception as e:
        st.error(f"Error geocoding address: {address}. Exception: {e}")
    return None, None

# Convert JSON to a DataFrame
locations = []
for day, places in data.items():
    for place in places:
        lat, lng = geocode_address(place["Address"])
        if lat and lng:
            locations.append({
                "Day": day,
                "Name": place["Name"],
                "Address": place["Address"],
                "Time": place.get("Time", "N/A"),  # Add time if available
                "Latitude": lat,
                "Longitude": lng,
                "Details": "; ".join(place["Details"])  # Convert details to a string for display
            })

df = pd.DataFrame(locations)

# Streamlit UI
st.title("Comedy Open Mic Locator")
st.markdown("Last updated: 1/3/2025")
st.markdown("Use left tab for filtering.")

# Day checkboxes
st.sidebar.header("Filter by Day")
days = df["Day"].unique()
selected_days = st.sidebar.multiselect("Select Days", options=days, default=days)

# Detail inclusion/exclusion filter
st.sidebar.header("Filter by Details")
all_details = set(detail for details in df["Details"].str.split("; ") for detail in details)
selected_details = st.sidebar.multiselect("Select Details", options=list(all_details))

# Toggle button to include or exclude based on details
filter_mode = st.sidebar.radio("Filter Mode", options=["Exclude", "Include"], index=0)

# Apply filters
filtered_df = df[df["Day"].isin(selected_days)]
if selected_details:
    if filter_mode == "Exclude":
        filtered_df = filtered_df[~filtered_df["Details"].apply(lambda x: any(detail in x for detail in selected_details))]
    elif filter_mode == "Include":
        filtered_df = filtered_df[filtered_df["Details"].apply(lambda x: any(detail in x for detail in selected_details))]

# Add interactive map
st.subheader("Map of Open Mics")
if not filtered_df.empty:
    # Define the map layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=filtered_df,
        get_position=["Longitude", "Latitude"],
        get_radius=100,
        get_fill_color=[255, 0, 0],
        pickable=True,  # Enable picking (hover events)
        auto_highlight=True,
    )

    # Define the tooltip
    tooltip = {
        "html": """
        <b>Name:</b> {Name}<br>
        <b>Time:</b> {Time}<br>
        <b>Details:</b> {Details}<br>
        <b>Address:</b> {Address}
        """,
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    # Create the Pydeck map
    view_state = pdk.ViewState(latitude=filtered_df["Latitude"].mean(), longitude=filtered_df["Longitude"].mean(), zoom=10)
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)

    st.pydeck_chart(r)
else:
    st.write("No locations to display.")

# Display filtered DataFrame below the map
st.subheader("Filtered Open Mics List")
if not filtered_df.empty:
    st.write(filtered_df[["Day", "Time", "Name", "Address", "Details"]])
else:
    st.write("No locations match your filters.")
