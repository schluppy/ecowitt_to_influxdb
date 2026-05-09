#!/usr/bin/env python3
#
# Receive Ecowitt format payloads and write them out to InfluxDB
#

import configparser
import sys
from flask import Flask, request
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Konfiguration einlesen
config = configparser.ConfigParser()
config.read('ecowitt.conf')

try:
    DEBUG = config.getboolean('settings', 'debug')
    PORT = config.getint('server', 'port')
    PASSKEY = config.get('server', 'passkey')
    INFLUX_URL = config.get('influxdb', 'url')
    INFLUX_TOKEN = config.get('influxdb', 'token')
    INFLUX_ORG = config.get('influxdb', 'org')
    INFLUX_BUCKET = config.get('influxdb', 'bucket')
except Exception as e:
    print(f"Fehler beim Laden der ecowitt.conf: {e}")
    sys.exit(1)

app = Flask(__name__)

# InfluxDB Client Initialisierung
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# --- Umrechnungsfunktionen ---

def f_to_c(val): 
    return round((float(val) - 32) * 5/9, 2) if val is not None else 0.0

def in_to_hpa(val): 
    return round(float(val) * 33.8639, 2) if val is not None else 0.0

def in_to_mm(val): 
    return round(float(val) * 25.4, 2) if val is not None else 0.0

def mph_to_kmh(val): 
    return round(float(val) * 1.60934, 2) if val is not None else 0.0

def kmh_to_bft(kmh):
    if kmh < 1.0: return 0
    elif kmh <= 5.0: return 1
    elif kmh <= 11.0: return 2
    elif kmh <= 19.0: return 3
    elif kmh <= 28.0: return 4
    elif kmh <= 38.0: return 5
    elif kmh <= 49.0: return 6
    elif kmh <= 61.0: return 7
    elif kmh <= 74.0: return 8
    elif kmh <= 88.0: return 9
    elif kmh <= 102.0: return 10
    elif kmh <= 117.0: return 11
    else: return 12

@app.route('/data/report/', methods=['POST'])
def receive_data():
    raw = request.form.to_dict()
    
    # Sicherheitscheck: Passkey
    if raw.get('PASSKEY') != PASSKEY:
        return "Unauthorized", 401

    try:
        # Grundwerte berechnen
        wind_kmh = mph_to_kmh(raw.get('windspeedmph'))
        
        # 1. Metrisches Daten-Dictionary erstellen
        m = {
            "temp_in_c": f_to_c(raw.get('tempinf')),
            "temp_out_c": f_to_c(raw.get('tempf')),
            "hum_in": int(raw.get('humidityin', 0)),
            "hum_out": int(raw.get('humidity', 0)),
            "press_rel_hpa": in_to_hpa(raw.get('baromrelin')),
            "press_abs_hpa": in_to_hpa(raw.get('baromabsin')),
            "wind_dir": int(raw.get('winddir', 0)),
            "wind_dir_avg10m": int(raw.get('winddir_avg10m', 0)),
            "wind_speed_kmh": wind_kmh,
            "wind_bft": kmh_to_bft(wind_kmh),
            "wind_gust_kmh": mph_to_kmh(raw.get('windgustmph')),
            "wind_max_daily_kmh": mph_to_kmh(raw.get('maxdailygust')),
            
            # Alle Piezo Regenwerte
            "rain_rate_mm": in_to_mm(raw.get('rrain_piezo')),
            "rain_event_mm": in_to_mm(raw.get('erain_piezo')),
            "rain_hour_mm": in_to_mm(raw.get('hrain_piezo')),
            "rain_24h_mm": in_to_mm(raw.get('last24hrain_piezo')),
            "rain_day_mm": in_to_mm(raw.get('drain_piezo')),
            "rain_week_mm": in_to_mm(raw.get('wrain_piezo')),
            "rain_month_mm": in_to_mm(raw.get('mrain_piezo')),
            "rain_year_mm": in_to_mm(raw.get('yrain_piezo')),
            
            # Licht und Sensordaten
            "solar_wm2": float(raw.get('solarradiation', 0.0)),
            "uv": int(raw.get('uv', 0)),
            "vpd": float(raw.get('vpd', 0.0)),
            "batt_volt": float(raw.get('wh90batt', 0.0)),
            "cap_volt": float(raw.get('ws90cap_volt', 0.0))
        }

        # 2. Debug-Ausgabe
        if DEBUG:
            print(f"\n{'='*75}")
            print(f" DATENPAKET EMPFANGEN: {raw.get('dateutc', 'N/A')}")
            print(f"{'='*75}")
            print(f"{'FELDNAME':<20} | {'ROHWERT':<15} | {'METRISCH'}")
            print(f"{'-'*75}")
            print(f"{'Temp Out':<20} | {raw.get('tempf', 'N/A') + ' F':<15} | {m['temp_out_c']} °C")
            print(f"{'Wind Speed':<20} | {raw.get('windspeedmph', 'N/A') + ' mph':<15} | {m['wind_speed_kmh']} km/h ({m['wind_bft']} Bft)")
            print(f"{'Rain Day':<20} | {raw.get('drain_piezo', 'N/A') + ' in':<15} | {m['rain_day_mm']} mm")
            print(f"{'Rain 24h':<20} | {raw.get('last24hrain_piezo', 'N/A') + ' in':<15} | {m['rain_24h_mm']} mm")
            print(f"{'Pressure Rel':<20} | {raw.get('baromrelin', 'N/A') + ' inHg':<15} | {m['press_rel_hpa']} hPa")
            print(f"{'Batt Volt':<20} | {raw.get('wh90batt', 'N/A') + ' V':<15} | {m['batt_volt']} V")
            print(f"{'-'*75}")
            print(f"ALLE ROHDATEN: {raw}")
            print(f"{'='*75}\n")

        # 3. InfluxDB Point bauen und schreiben
        p = Point("weather_station").tag("model", raw.get('model', 'Unknown'))
        for field, value in m.items():
            p.field(field, value)

        write_api.write(INFLUX_BUCKET, INFLUX_ORG, p)
        return "OK", 200

    except Exception as e:
        print(f"!!! FEHLER BEI VERARBEITUNG: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
