````markdown
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
````

2. **Create & activate your virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   python app.py
   ```

   Then open the local URL printed by Gradio (e.g. `http://127.0.0.1:7860`).

---

## 🔧 Configuration

* Caches are stored in `.cache_sat/` and `.cache_climate/` (expire after 1 hour).
* Default timezone is **Asia/Kolkata**.
* Country filtered to **IN** in geocoding.

You can tweak tile layers via the “Tileset” dropdown (OpenStreetMap, CartoDB).

---

## 📁 Repository Structure

```
.
├── app.py               # Main Gradio + Folium application
├── requirements.txt     # Python dependencies
└── README.md            # This documentation
```

---

## 📦 requirements.txt

```text
folium
gradio
requests
requests-cache
pandas
pytz
retry-requests
openmeteo-requests
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/foo`)
3. Commit your changes (`git commit -am 'Add foo'`)
4. Push to the branch (`git push origin feature/foo`)
5. Open a Pull Request

---

## 📝 License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## 👤 Author

**Partha Pratim Ray**
✉️ [parthapratimray1986@gmail.com](mailto:parthapratimray1986@gmail.com)

```

Feel free to adjust any section as needed!
```
