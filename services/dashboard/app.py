import streamlit as st
import requests

API_URL = "http://localhost:5000"

st.set_page_config(page_title="AirTrail Dashboard", layout="wide")

st.title("AirTrail Platform ☁️📉")
st.write("Personal Pollution Exposure Analytics")

tab1, tab2, tab3 = st.tabs(["Upload GPS Trace", "Exposure Results", "Location Explorer"])

with tab1:
    st.header("Upload GPS Trace")
    uploaded_file = st.file_uploader("Choose a CSV or GPX file", type=["csv", "gpx"])
    if uploaded_file is not None:
        if st.button("Upload and Process"):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/plain")}
            response = requests.post(f"{API_URL}/api/v1/traces", files=files)
            if response.status_code == 201:
                st.success("File uploaded and submitted for processing!")
                st.json(response.json())
            else:
                st.error("Upload failed.")

with tab2:
    st.header("Exposure Results")
    trace_id = st.text_input("Enter Trace ID to view results")
    if st.button("Fetch Results"):
        st.info("Fetching results from API (stub)")
        # stub for fetching results from db/redis
        st.metric(label="Cumulative Exposure", value="154.2 µg/m³", delta="1.2")

with tab3:
    st.header("Location Explorer")
    st.write("Query average pollution for a specific location and radius.")
    col1, col2, col3 = st.columns(3)
    with col1:
        lat = st.number_input("Latitude", value=37.7749)
    with col2:
        lon = st.number_input("Longitude", value=-122.4194)
    with col3:
        radius = st.number_input("Radius (m)", value=5000)
        
    if st.button("Analyze Location"):
        st.info("Analyzing location (stub)")
        st.line_chart([10, 15, 13, 20, 25, 22, 18])

