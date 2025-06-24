import folium
import gradio as gr
import requests
import requests_cache
import pandas as pd
import datetime
import pytz

from retry_requests import retry
import openmeteo_requests

# ----------------------------------------------------------------
# Setup Satellite Radiation API client (with cache & retry)
# ----------------------------------------------------------------
cache_session = requests_cache.CachedSession('.cache_sat', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
satellite_client = openmeteo_requests.Client(session=retry_session)

# ----------------------------------------------------------------
# AQI breakpoints per CPCB (for index range 0–500, six bands)
# ----------------------------------------------------------------
AQI_BREAKPOINTS = {
    "pm2_5": [ (0,30,0,50), (30,60,51,100), (60,90,101,200),
               (90,120,201,300), (120,250,301,400), (250,350,401,500) ],
    "pm10":  [ (0,50,0,50), (50,100,51,100), (100,250,101,200),
               (250,350,201,300), (350,430,301,400), (430,600,401,500) ],
    "carbon_monoxide": [ (0,1,0,50), (1,2,51,100), (2,10,101,200),
                         (10,17,201,300), (17,34,301,400), (34,50,401,500) ],
    "nitrogen_dioxide":[ (0,40,0,50), (40,80,51,100), (80,180,101,200),
                         (180,280,201,300), (280,400,301,400), (400,1000,401,500) ],
    "sulphur_dioxide": [ (0,40,0,50), (40,80,51,100), (80,380,101,200),
                         (380,800,201,300), (800,1600,301,400), (1600,2000,401,500) ],
    "ozone":            [ (0,50,0,50), (50,100,51,100), (100,168,101,200),
                         (168,208,201,300), (208,748,301,400), (748,1000,401,500) ],
}

AQI_BANDS = [
    (0, 50,    "Good",        "#009966"),
    (51,100,   "Satisfactory","#ffde33"),
    (101,200,  "Moderate",    "#ff9933"),
    (201,300,  "Poor",        "#cc0033"),
    (301,400,  "Very Poor",   "#660099"),
    (401,500,  "Severe",      "#7e0023"),
]

TILE_OPTIONS = [
    ("OpenStreetMap", "OpenStreetMap", None),
    ("CartoDB positron", "CartoDB positron", None),
]

CUSTOM_TILES = {}

# ----------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------
def sub_index(C, breakpoints):
    for C_low, C_high, I_low, I_high in breakpoints:
        if C_low <= C <= C_high:
            return ((I_high - I_low)/(C_high - C_low)) * (C - C_low) + I_low
    if C < breakpoints[0][0]:
        return breakpoints[0][2]
    return breakpoints[-1][3]

def aqi_color(aqi):
    for low, high, label, color in AQI_BANDS:
        if low <= aqi <= high:
            return color, label
    return "#000000", "Unknown"

def is_within_india(lat, lon):
    return 6.0 <= lat <= 36.0 and 68.0 <= lon <= 98.0

# -------------------------------------------------------------
# Climate data
# -------------------------------------------------------------
def get_climate_data(lat, lon, location_name, date_str):
    cache_session = requests_cache.CachedSession('.cache_climate', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    climate_client = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "models": [
            "CMCC_CM2_VHR4", "FGOALS_f3_H", "HiRAM_SIT_HR", "MRI_AGCM3_2_S",
            "EC_Earth3P_HR", "MPI_ESM1_2_XR", "NICAM16_8S"
        ],
        "daily": [
            "temperature_2m_max", "temperature_2m_mean", "temperature_2m_min",
            "wind_speed_10m_mean", "wind_speed_10m_max", "cloud_cover_mean",
            "shortwave_radiation_sum", "relative_humidity_2m_mean",
            "relative_humidity_2m_max", "relative_humidity_2m_min",
            "dew_point_2m_mean", "dew_point_2m_min", "dew_point_2m_max",
            "precipitation_sum", "rain_sum", "snowfall_sum", "pressure_msl_mean",
            "soil_moisture_0_to_10cm_mean", "et0_fao_evapotranspiration_sum"
        ]
    }

    try:
        responses = climate_client.weather_api(
            "https://climate-api.open-meteo.com/v1/climate",
            params=params
        )
        resp = responses[0]
        daily = resp.Daily()

        VAR_LABELS = [
            ("temperature_2m_max", "Temp Max (°C)"),
            ("temperature_2m_mean", "Temp Mean (°C)"),
            ("temperature_2m_min", "Temp Min (°C)"),
            ("wind_speed_10m_mean", "Wind 10m Mean (m/s)"),
            ("wind_speed_10m_max", "Wind 10m Max (m/s)"),
            ("cloud_cover_mean", "Cloud Cover Mean (%)"),
            ("shortwave_radiation_sum", "Shortwave Rad. Sum (MJ/m²)"),
            ("relative_humidity_2m_mean", "RH Mean (%)"),
            ("relative_humidity_2m_max", "RH Max (%)"),
            ("relative_humidity_2m_min", "RH Min (%)"),
            ("dew_point_2m_mean", "Dew Point Mean (°C)"),
            ("dew_point_2m_min", "Dew Point Min (°C)"),
            ("dew_point_2m_max", "Dew Point Max (°C)"),
            ("precipitation_sum", "Precipitation Sum (mm)"),
            ("rain_sum", "Rain Sum (mm)"),
            ("snowfall_sum", "Snowfall Sum (mm)"),
            ("pressure_msl_mean", "Pressure MSL Mean (hPa)"),
            ("soil_moisture_0_to_10cm_mean", "Soil Moisture 0–10cm Mean (m³/m³)"),
            ("et0_fao_evapotranspiration_sum", "ET₀ FAO Evapotransp. (mm)"),
        ]

        html_rows = ""
        for i, (_, label) in enumerate(VAR_LABELS):
            val = daily.Variables(i).ValuesAsNumpy()[0] \
                  if daily.Variables(i).ValuesAsNumpy().size > 0 else "-"
            html_rows += f"<tr><td>{label}</td><td>{val}</td></tr>"

        return f"""
        <div style="padding:1em;border:1px solid #87ceeb;border-radius:8px;max-width:100%;margin-top:1em;">
            <h4 style="margin-bottom:.3em;">
                🌦️ Climate Data {location_name} ({date_str})
            </h4>
            <table style="width:100%;font-size:.92em;">{html_rows}</table>
        </div>
        """
    except Exception as e:
        return f"<div style='color:red;padding:.5em;'>Climate data unavailable: {e}</div>"

# ----------------------------------------------------------------
# Satellite radiation (sunrise, sunset, terrestrial_radiation_instant)
# ----------------------------------------------------------------
def get_satellite_radiation(lat, lon, location_name, date_str):
    tz = pytz.timezone("Asia/Kolkata")
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date.isoformat(),
        "end_date": date.isoformat(),
        "timezone": "Asia/Kolkata",
        "daily": ["sunrise","sunset"],
        "hourly": ["terrestrial_radiation_instant"],
        "models": "satellite_radiation_seamless"
    }

    responses = satellite_client.weather_api(
        "https://satellite-api.open-meteo.com/v1/archive",
        params=params
    )
    resp = responses[0]

    daily = resp.Daily()
    srise = pd.to_datetime(
        daily.Variables(0).ValuesInt64AsNumpy()[0], unit="s", utc=True
    ).tz_convert(tz).strftime("%H:%M")
    sset  = pd.to_datetime(
        daily.Variables(1).ValuesInt64AsNumpy()[0], unit="s", utc=True
    ).tz_convert(tz).strftime("%H:%M")

    hourly = resp.Hourly()
    times = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True).tz_convert(tz),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True).tz_convert(tz),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )
    ter_inst = hourly.Variables(0).ValuesAsNumpy()
    hourly_df = pd.DataFrame({
        "datetime_ist": times,
        "terrestrial_radiation_instant": ter_inst
    })
    hourly_html = hourly_df.to_html(index=False, border=0, classes="dataframe", justify="center")

    return f"""
    <div style="padding:1em;border:1px solid #f3b86a;border-radius:8px;max-width:100%;margin-top:1em;">
      <h4 style="margin-top:1em;margin-bottom:.2em;">
        ☀️ Satellite Radiation {location_name} ({date_str})
      </h4>
      <table style="width:100%;font-size:.9em;">
        <tr><td>Sunrise (IST):</td><td>{srise}</td></tr>
        <tr><td>Sunset (IST):</td><td>{sset}</td></tr>
      </table>
      <br>
      <h5 style='margin-top:1em;'>📈 Hourly Terrestrial Radiation Instant</h5>
      {hourly_html}
    </div>
    """

# ----------------------------------------------------------------
# Air quality + extras
# ----------------------------------------------------------------
def get_air_quality(lat, lon, location_name, date_str):
    params = {
        "latitude": lat, "longitude": lon,
        "current": [
            "pm2_5","pm10","carbon_monoxide",
            "nitrogen_dioxide","sulphur_dioxide","ozone",
            "aerosol_optical_depth","dust",
            "uv_index","uv_index_clear_sky","methane"
        ]
    }
    resp = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params=params, timeout=5
    )
    resp.raise_for_status()
    c = resp.json().get("current", {})

    pm25 = c.get("pm2_5",0); pm10 = c.get("pm10",0)
    co   = c.get("carbon_monoxide",0)/1000.0
    no2  = c.get("nitrogen_dioxide",0); so2 = c.get("sulphur_dioxide",0)
    o3   = c.get("ozone",0)

    idx_pm25 = sub_index(pm25, AQI_BREAKPOINTS["pm2_5"])
    idx_pm10 = sub_index(pm10, AQI_BREAKPOINTS["pm10"])
    idx_co   = sub_index(co,   AQI_BREAKPOINTS["carbon_monoxide"])
    idx_no2  = sub_index(no2,  AQI_BREAKPOINTS["nitrogen_dioxide"])
    idx_so2  = sub_index(so2,  AQI_BREAKPOINTS["sulphur_dioxide"])
    idx_o3   = sub_index(o3,   AQI_BREAKPOINTS["ozone"])
    aqi = max(idx_pm25, idx_pm10, idx_co, idx_no2, idx_so2, idx_o3)
    color, label = aqi_color(aqi)

    aod  = c.get("aerosol_optical_depth",0)
    dust = c.get("dust",0)
    uv   = c.get("uv_index",0)
    uvcs = c.get("uv_index_clear_sky",0)
    ch4  = c.get("methane",0)

    legend_spans = "".join(
        f"<span style='display:inline-block;padding:.2em .6em;margin:.1em;"
        f"border-radius:4px;background:{col};color:#fff;font-size:.8em;'>{lbl}</span>"
        for _,_,lbl,col in AQI_BANDS
    )

    return f"""
    <div style="padding:1em;border:1px solid #ddd;border-radius:8px;max-width:100%;margin-top:1em;">
      <h4 style="margin-bottom:.2em;">
        🌿 Air Quality Index (AQI) of {location_name} ({date_str})
      </h4>
      <div style="display:flex;align-items:center;">
        <div style="width:60px;height:60px;background:{color};
                    border-radius:50%;display:flex;align-items:center;
                    justify-content:center;font-size:1.25em;color:white;
                    margin-right:1em;">
          {int(aqi)}
        </div>
        <div><strong>{label}</strong></div>
      </div>
      <table style="width:100%;margin-top:.5em;font-size:.9em;">
        <tr><td>PM₂.₅:</td><td>{pm25} μg/m³ → {idx_pm25:.0f}</td></tr>
        <tr><td>PM₁₀:</td><td>{pm10} μg/m³ → {idx_pm10:.0f}</td></tr>
        <tr><td>CO:</td><td>{co:.3f} mg/m³ → {idx_co:.0f}</td></tr>
        <tr><td>NO₂:</td><td>{no2} μg/m³ → {idx_no2:.0f}</td></tr>
        <tr><td>SO₂:</td><td>{so2} μg/m³ → {idx_so2:.0f}</td></tr>
        <tr><td>O₃:</td><td>{o3} μg/m³ → {idx_o3:.0f}</td></tr>
        <tr><td>AOD:</td><td>{aod}</td></tr>
        <tr><td>Dust:</td><td>{dust}</td></tr>
        <tr><td>UV Index:</td><td>{uv}</td></tr>
        <tr><td>UV Index Clear Sky:</td><td>{uvcs}</td></tr>
        <tr><td>Methane (CH₄):</td><td>{ch4} ppm</td></tr>
      </table>
      <div style="margin-top:1em;">
        <strong>Legend (AQI bands):</strong> {legend_spans}
      </div>
    </div>
    """

# ----------------------------------------------------------------
# Geocoding + Map
# ----------------------------------------------------------------
def search_location_open_meteo(location_name):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name":location_name,"count":5,"language":"en","format":"json","countryCode":"IN"}
    resp = requests.get(url, params=params, timeout=5); resp.raise_for_status()
    for res in resp.json().get("results",[]):
        if res.get("country_code") == "IN":
            admin = ", ".join(filter(None,[
                res.get("admin1",""),res.get("admin2",""),
                res.get("admin3",""),res.get("admin4","")
            ]))
            return {
                "lat":res["latitude"], "lon":res["longitude"],
                "admin":admin,
                "display":f"{res['name']} ({res['latitude']:.4f}, {res['longitude']:.4f})"
            }
    return None

def create_india_map(lat=None, lon=None, zoom_start=5, tiles_label="OpenStreetMap"):
    try:
        tile_info = next((t for t in TILE_OPTIONS if t[0]==tiles_label), None)
        if tile_info:
            tiles, attr = tile_info[1], tile_info[2]
        elif tiles_label in CUSTOM_TILES:
            tiles, attr = CUSTOM_TILES[tiles_label]
        else:
            tiles, attr = "OpenStreetMap", None

        map_args = {"location":[21.146633,79.088860],"zoom_start":zoom_start}
        if attr:
            map_args.update(tiles=tiles, attr=attr)
        else:
            map_args.update(tiles=tiles)

        m = folium.Map(**map_args)
        if lat is not None and lon is not None:
            lat_f, lon_f = float(lat), float(lon)
            if not is_within_india(lat_f, lon_f):
                folium.Marker(
                    [21.146633,79.088860],
                    popup=folium.Popup("Out of India bounds",max_width=200),
                    icon=folium.Icon(color="red")
                ).add_to(m)
            else:
                folium.Marker(
                    [lat_f,lon_f],
                    tooltip="Location",
                    popup=folium.Popup(
                        f"Lat: {lat_f:.4f}, Lon: {lon_f:.4f}",max_width=200
                    ),
                    icon=folium.Icon(color="blue",icon="info-sign")
                ).add_to(m)

        return (
            "<div style='border-radius:18px;box-shadow:0 4px 18px #8882;"
            "overflow:hidden;margin:1em 0;min-height:520px;max-width:100%;'>"
            + m._repr_html_() +
            "</div>"
        )
    except Exception as e:
        return f"<div style='color:red;padding:1em;'>Error generating map: {e}</div>"

# ----------------------------------------------------------------
# Gradio callbacks
# ----------------------------------------------------------------
def search_and_set_location(name, zoom, tiles):
    if not name or len(name.strip())<3:
        return (
            gr.update(value=None), gr.update(value=None),
            "❌ Enter ≥3 chars",
            create_india_map(None,None,zoom,tiles),
            ""
        )

    r = search_location_open_meteo(name.strip())
    if not r:
        return (
            gr.update(value=None), gr.update(value=None),
            "❌ Not found/India",
            create_india_map(None,None,zoom,tiles),
            ""
        )

    lat, lon = r["lat"], r["lon"]
    msg = f"✅ <b>Found:</b> {r['display']}<br><i>{r['admin']}</i>"
    location_display = r["display"]
    today = datetime.datetime.now(
        pytz.timezone("Asia/Kolkata")
    ).strftime("%Y-%m-%d")

    aqi_html     = get_air_quality(lat, lon, location_display, today)
    sat_html     = get_satellite_radiation(lat, lon, location_display, today)

    return (
        gr.update(value=lat),
        gr.update(value=lon),
        msg,
        create_india_map(lat, lon, zoom, tiles),
        aqi_html + sat_html
    )

def manual_update(lat, lon, zoom, tiles):
    if lat is not None and lon is not None and is_within_india(lat, lon):
        location_display = f"{lat:.4f}, {lon:.4f}"
        msg = f"✅ Marker at ({location_display})"
        today = datetime.datetime.now(
            pytz.timezone("Asia/Kolkata")
        ).strftime("%Y-%m-%d")

        aqi_html     = get_air_quality(lat, lon, location_display, today)
        sat_html     = get_satellite_radiation(lat, lon, location_display, today)
        climate_html = get_climate_data(lat, lon, location_display, today)

        html = aqi_html + sat_html + climate_html
    else:
        msg, html = "ℹ️ Enter valid India coords or search", ""

    return (lat, lon, msg, create_india_map(lat, lon, zoom, tiles), html)

# ----------------------------------------------------------------
# Build UI
# ----------------------------------------------------------------
def build_ui():
    desc = """
    <div style="font-size:1.15em;line-height:1.6;padding:0 0 18px 0;">
      <b style="font-size:1.23em;color:#204466;">
        India Map + AQI, Satellite & Climate Data
      </b><br>
      <ul>
        <li>🔍 Search Indian location: marker + AQI + satellite + climate</li>
        <li>📍 Or enter lat/lon (6–36, 68–98) manually</li>
        <li>🔄 Adjust zoom & tileset</li>
      </ul>
    </div>
    """
    with gr.Blocks(css=".gradio-container{background:#f9fafb;}") as demo:
        gr.HTML(desc)
        with gr.Row():
            sb = gr.Textbox(label="Search Location", placeholder="E.g., Mumbai")
        with gr.Row():
            la = gr.Number(label="Latitude", info="6–36")
            lo = gr.Number(label="Longitude", info="68–98")
        with gr.Row():
            zm = gr.Slider(1,18,step=1,value=5,label="Zoom")
            tl = gr.Dropdown(
                choices=[t[0] for t in TILE_OPTIONS] + list(CUSTOM_TILES.keys()),
                value="OpenStreetMap", label="Tileset"
            )
        msg = gr.HTML()
        mp  = gr.HTML(label="Map")
        dt  = gr.HTML(label="Data")

        sb.submit(
            search_and_set_location,
            [sb, zm, tl],
            [la, lo, msg, mp, dt],
            show_progress=True
        )
        for inp in (la, lo, zm, tl):
            inp.change(
                manual_update,
                [la, lo, zm, tl],
                [la, lo, msg, mp, dt]
            )
        demo.load(
            lambda z, t: manual_update(None, None, z, t),
            [zm, tl],
            [la, lo, msg, mp, dt]
        )

    return demo

if __name__ == "__main__":
    build_ui().launch()

