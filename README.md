# India Map + AQI, Satellite & Climate Data

A simple Gradio web application that lets you search for any location in India (or enter lat/lon manually) and displays:

- 📍 An interactive Folium map  
- 🌿 **Air Quality Index (AQI)** and related pollutants  
- ☀️ **Satellite Radiation** (sunrise/sunset and hourly terrestrial radiation)  
- 🌦️ **Climate Data** (daily summary from multiple climate models)

---

## 📋 Features

- **Search by name** (uses Open-Meteo geocoding API)  
- **Manual coordinates** input (latitude 6–36, longitude 68–98)  
- **Cached & retried** API calls for reliability  
- **Responsive** UI with Gradio + Folium  
- **Styled** data panels with live date & location in headers  

---

## 🚀 Quick Start

1. **Clone the repo**  
   ```bash
   git clone https://github.com/parthapratimray1986/india-aqi-satellite-climate.git
   cd india-aqi-satellite-climate
