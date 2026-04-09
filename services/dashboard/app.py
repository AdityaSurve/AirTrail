import os
import time
from datetime import datetime, timedelta

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from packages.airtrail_core.ingestion import parse_csv_trace

API_URL = os.getenv("API_URL", "http://localhost:5000")

st.set_page_config(page_title="AirTrail Dashboard", layout="wide")

st.title("AirTrail Platform")
st.caption("Personal pollution exposure analytics")

tab_upload, tab_point = st.tabs(["Upload GPS / CSV", "Check a single location"])


def _api_bases() -> list[str]:
    configured = (API_URL or "").rstrip("/")
    bases = []
    if configured:
        bases.append(configured)
    for b in ("http://localhost:5000", "http://api:5000"):
        if b not in bases:
            bases.append(b)
    return bases


def _api_request(method: str, path: str, **kwargs) -> requests.Response:
    last_exc = None
    for base in _api_bases():
        try:
            return requests.request(method, f"{base}{path}", **kwargs)
        except requests.RequestException as e:
            last_exc = e
            continue
    raise requests.RequestException(f"All API endpoints failed ({_api_bases()})") from last_exc


def _poll_job(job_id: int, timeout_s: float = 120.0, interval_s: float = 2.0) -> dict | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        r = _api_request("GET", f"/api/v1/jobs/{job_id}", timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        status = data.get("status")
        if status == "SUCCESS":
            return data
        if status == "FAILURE":
            err = data.get("error") or "unknown"
            raise RuntimeError(err)
        time.sleep(interval_s)
    return None


def _build_exposure_map(points: list[dict]) -> folium.Map:
    valid = [p for p in points if p.get("lat") is not None and p.get("lon") is not None]
    if not valid:
        return folium.Map(location=[37.7749, -122.4194], zoom_start=10, tiles="CartoDB positron")
    clat = sum(p["lat"] for p in valid) / len(valid)
    clon = sum(p["lon"] for p in valid) / len(valid)
    m = folium.Map(location=[clat, clon], zoom_start=12, tiles="CartoDB positron")
    fg = folium.FeatureGroup(name="Exposure points")
    for p in valid:
        conc = p.get("matched_concentration")
        conc_s = f"{conc:.2f} µg/m³" if conc is not None else "n/a"
        site = p.get("site_name") or "—"
        sid = p.get("matched_site_id")
        ts = p.get("timestamp") or "—"
        tip_html = (
            f"<div style='min-width:160px;font-size:12px;line-height:1.35'>"
            f"<b>Time</b><br>{ts}<br>"
            f"<b>PM2.5</b><br>{conc_s}<br>"
            f"<b>Site</b><br>{site}<br>"
            f"<b>Site id</b><br>{sid}<br>"
            f"<b>Lat / Lon</b><br>{p['lat']:.5f}, {p['lon']:.5f}"
            f"</div>"
        )
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=4,
            color="#1d6f42",
            weight=1,
            fill=True,
            fillColor="#44c762",
            fillOpacity=0.42,
            tooltip=folium.Tooltip(tip_html, sticky=True),
        ).add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


with tab_upload:
    st.subheader("Upload GPS trace (CSV)")
    st.write("CSV must include columns: `timestamp`, `lat`, `lon`. Processing matches each point to nearby monitoring data.")

    uploaded = st.file_uploader("Choose a CSV file", type=["csv", "gpx"])

    t_min = t_max = None
    if uploaded is not None:
        if uploaded.name.lower().endswith(".csv"):
            try:
                recs = parse_csv_trace(uploaded.getvalue())
                ts = [r["timestamp"] for r in recs]
                t_min, t_max = min(ts), max(ts)
                st.session_state["upload_t_min"] = t_min
                st.session_state["upload_t_max"] = t_max
            except Exception as e:
                st.warning(f"Could not parse CSV for time range: {e}")
        else:
            st.info("GPX time range preview is not available; after processing, use the full trace time window from stored results.")

    if t_min is None and "upload_t_min" in st.session_state:
        t_min = st.session_state["upload_t_min"]
        t_max = st.session_state["upload_t_max"]

    if t_min is not None and t_max is not None:
        filt = st.slider(
            "Filter map by time (from your file)",
            min_value=t_min,
            max_value=t_max,
            value=(t_min, t_max),
            format="MM/DD HH:mm",
            key="upload_time_slider",
        )
    else:
        filt = None

    go = st.button("Upload and process", type="primary", disabled=uploaded is None)

    if go and uploaded is not None:
        mime = "text/csv" if uploaded.name.lower().endswith(".csv") else "application/octet-stream"
        files = {"file": (uploaded.name, uploaded.getvalue(), mime)}
        try:
            resp = _api_request("POST", "/api/v1/traces", files=files, timeout=120)
        except requests.RequestException as e:
            st.error(f"Upload failed: {e}")
        else:
            if resp.status_code != 201:
                st.error(f"Upload failed: {resp.text}")
            else:
                body = resp.json()
                st.session_state["last_trace_id"] = body["trace_id"]
                st.session_state["last_job_id"] = body["job_id"]
                st.session_state["poll_after_upload"] = True
                st.success(f"Queued job **{body['job_id']}** for trace **{body['trace_id']}**.")

    trace_id = st.session_state.get("last_trace_id")
    job_id = st.session_state.get("last_job_id")

    if trace_id and job_id:
        refresh = st.button("Refresh job status / load map")

        if refresh or st.session_state.pop("poll_after_upload", False):
            exp = _api_request("GET", f"/api/v1/traces/{trace_id}/exposure", timeout=30)
            if exp.status_code == 404:
                with st.spinner("Waiting for worker (up to 2 min)…"):
                    try:
                        _poll_job(job_id)
                    except RuntimeError as e:
                        st.error(str(e))

        status = _api_request("GET", f"/api/v1/jobs/{job_id}", timeout=30)
        if status.ok:
            sj = status.json()
            st.write(f"Job **{job_id}**: **{sj.get('status')}**")
            if sj.get("status") == "FAILURE" and sj.get("error"):
                st.error(sj["error"])

        exp = _api_request("GET", f"/api/v1/traces/{trace_id}/exposure", timeout=30)
        if exp.status_code == 200:
            m = exp.json()
            c1, c2, c3 = st.columns(3)
            c1.metric("Cumulative exposure", f"{m.get('cumulative', 0):.2f}")
            c2.metric("Mean", f"{m.get('mean', 0):.2f}")
            c3.metric("Peak", f"{m.get('peak', 0):.2f}")
        elif exp.status_code == 404:
            st.info("Exposure results not ready yet — click **Refresh job status / load map** after the worker finishes.")

        params = {}
        if filt is not None:
            params["start"] = filt[0].isoformat()
            params["end"] = filt[1].isoformat()

        pr = _api_request(
            "GET",
            f"/api/v1/traces/{trace_id}/exposure/points",
            params=params,
            timeout=60,
        )
        if pr.status_code == 200:
            pts = pr.json().get("points") or []
            exp_ok = exp.status_code == 200
            if pts:
                st.subheader("Exposure along your route")
                st_folium(
                    _build_exposure_map(pts),
                    width=None,
                    height=480,
                    use_container_width=True,
                )
            elif exp_ok:
                st.warning("No points in the selected time range.")
        elif pr.status_code != 200 and exp.status_code == 200:
            st.warning("Could not load map points.")

with tab_point:
    st.subheader("Pollution at one location")
    st.write("Enter coordinates or **click the map** to set latitude and longitude, then query monitoring observations nearby.")

    now = datetime.utcnow()
    win_start = now - timedelta(days=30)

    if "inp_lat" not in st.session_state:
        st.session_state.inp_lat = 37.7749
    if "inp_lon" not in st.session_state:
        st.session_state.inp_lon = -122.4194
    if "map_pending_lat" in st.session_state and "map_pending_lon" in st.session_state:
        st.session_state.inp_lat = st.session_state.pop("map_pending_lat")
        st.session_state.inp_lon = st.session_state.pop("map_pending_lon")

    t_range = st.slider(
        "Observation time range (within the last 30 days)",
        min_value=win_start,
        max_value=now,
        value=(win_start, now),
        format="MM/DD HH:mm",
        key="single_point_time",
    )

    mc, ic = st.columns((1.4, 1))
    with ic:
        lat = st.number_input("Latitude", format="%.6f", key="inp_lat")
        lon = st.number_input("Longitude", format="%.6f", key="inp_lon")
        radius = st.number_input("Search radius (m)", min_value=100, max_value=50000, value=5000, step=100)
        run_q = st.button("Get results", type="primary")

    with mc:
        m2 = folium.Map(
            location=[float(st.session_state.inp_lat), float(st.session_state.inp_lon)],
            zoom_start=11,
            tiles="CartoDB positron",
        )
        folium.Marker(
            [float(st.session_state.inp_lat), float(st.session_state.inp_lon)],
            tooltip="Selected point (edit in the panel or click map)",
        ).add_to(m2)
        folium.LatLngPopup().add_to(m2)
        out = st_folium(
            m2,
            height=420,
            use_container_width=True,
            key="folium_single",
        )
        if out and out.get("last_clicked"):
            lc = out["last_clicked"]
            if lc.get("lat") is not None and lc.get("lng") is not None:
                st.session_state["map_pending_lat"] = lc["lat"]
                st.session_state["map_pending_lon"] = lc["lng"]
                st.rerun()

    if run_q:
        payload = {
            "lat": lat,
            "lon": lon,
            "start": t_range[0].isoformat(),
            "end": t_range[1].isoformat(),
            "radius_m": int(radius),
        }
        try:
            r = _api_request("POST", "/api/v1/analytics/location", json=payload, timeout=60)
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
        else:
            if r.status_code != 200:
                st.error(r.text)
            else:
                d = r.json()
                st.metric("Average PM2.5 (µg/m³)", f"{d['average']:.2f}" if d.get("average") is not None else "—")
                st.metric("Observations used", d.get("observation_count", 0))
                series = d.get("series") or []
                if series:
                    df = pd.DataFrame(
                        {"time": [datetime.fromisoformat(x["t"]) for x in series], "value": [x["value"] for x in series]}
                    )
                    st.line_chart(df.set_index("time"))
                else:
                    st.info("No observations in this window and radius.")
