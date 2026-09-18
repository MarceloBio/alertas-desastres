import os
import requests
from datetime import datetime, timedelta, timezone
from math import radians, cos, sin, asin, sqrt

# ====================== CONFIGURACIÓN ======================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

LOCATIONS = [
    {
        "name": "Vitoria-Gasteiz (España)",
        "lat": 42.85,
        "lon": -2.67,
        "radius_km": 200
    },
    {
        "name": "La Plata (Argentina)",
        "lat": -34.921,
        "lon": -57.954,
        "radius_km": 250
    }
]

MIN_MAGNITUDE = 4.5
# ==========================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def check_usgs_earthquakes():
    alerts = []
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=6)

    for loc in LOCATIONS:
        url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson"
            f"&starttime={start.strftime('%Y-%m-%dT%H:%M:%S')}"
            f"&endtime={end.strftime('%Y-%m-%dT%H:%M:%S')}"
            f"&latitude={loc['lat']}&longitude={loc['lon']}"
            f"&maxradiuskm={loc['radius_km']}"
            f"&minmagnitude={MIN_MAGNITUDE}"
            "&orderby=time"
        )
        try:
            r = requests.get(url, timeout=20)
            data = r.json()
            for feature in data.get("features", []):
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                mag = props.get("mag")
                place = props.get("place", "Desconocido")
                time_eq = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc)
                dist = haversine(loc["lat"], loc["lon"], coords[1], coords[0])

                msg = (
                    f"🚨 <b>TERREMOTO cerca de {loc['name']}</b>\n"
                    f"Magnitud: <b>{mag}</b>\n"
                    f"Lugar: {place}\n"
                    f"Distancia aprox.: {dist:.0f} km\n"
                    f"Hora (UTC): {time_eq.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Más info: {props.get('url', '')}"
                )
                alerts.append(msg)
        except Exception as e:
            print(f"Error USGS ({loc['name']}): {e}")
    return alerts

def check_gdacs():
    alerts = []
    url = "https://www.gdacs.org/xml/rss.xml"
    try:
        r = requests.get(url, timeout=15)
        content = r.text.lower()
        if "orange" in content or "red" in content:
            msg = (
                "⚠️ <b>Alerta GDACS (Naranja o Roja)</b>\n"
                "Hay eventos importantes activos en el mundo.\n"
                "Revisa el mapa: https://www.gdacs.org/"
            )
            alerts.append(msg)
    except Exception as e:
        print(f"Error GDACS: {e}")
    return alerts

def check_extreme_weather():
    alerts = []
    for loc in LOCATIONS:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={loc['lat']}&longitude={loc['lon']}"
            "&current=temperature_2m,weather_code,wind_speed_10m,precipitation"
            "&timezone=auto"
        )
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            current = data.get("current", {})
            code = current.get("weather_code", 0)
            wind = current.get("wind_speed_10m", 0)
            precip = current.get("precipitation", 0)
            temp = current.get("temperature_2m", 0)

            extreme_codes = [65, 66, 67, 75, 82, 85, 86, 95, 96, 99]
            if code in extreme_codes or wind >= 60 or precip >= 15:
                msg = (
                    f"⛈️ <b>Clima extremo en {loc['name']}</b>\n"
                    f"Temperatura: {temp}°C\n"
                    f"Viento: {wind} km/h\n"
                    f"Precipitación: {precip} mm\n"
                    f"Código tiempo: {code}"
                )
                alerts.append(msg)
        except Exception as e:
            print(f"Error Open-Meteo ({loc['name']}): {e}")
    return alerts

def main():
    print(f"[{datetime.now()}] Revisando alertas...")

    all_alerts = []
    all_alerts.extend(check_usgs_earthquakes())
    all_alerts.extend(check_gdacs())
    all_alerts.extend(check_extreme_weather())

    if all_alerts:
        for alert in all_alerts:
            send_telegram(alert)
            print("Alerta enviada")
    else:
        print("No hay alertas nuevas.")

if __name__ == "__main__":
    main()