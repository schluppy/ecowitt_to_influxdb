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
    # Passkey einlesen und Leerzeichen entfernen
    CONF_PASSKEY = config.get('server', 'passkey').strip()
    
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

# --- Metrische Umrechnungsfunktionen ---

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
    recv_key = raw.get('PASSKEY')
    
    # --- PASSKEY LOGIK ---
    if CONF_PASSKEY.upper() != "NONE":
        if recv_key != CONF_PASSKEY:
            if DEBUG: 
                print(f"!!! ZUGRIFF VERWEIGERT: Falscher Passkey: {recv_key}")
            return "Unauthorized", 401
    elif DEBUG:
        # Im Lern-Modus (NONE) zeigen wir den Key prominent an
        print(f"\n{'*' * 70}")
        print(f" LERN-MODUS AKTIV! Empfangener PASSKEY: {recv_key}")
        print(f" Bitte diesen Key in der ecowitt.conf eintragen.")
        print(f"{'*' * 70}")

    try:
        # Grundwerte für Wind berechnen
        wind_kmh = mph_to_kmh(raw.get('windspeedmph'))
        
        # 1. Metrische Daten zusammenstellen
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
            
            # Alle Piezo Regenwerte (mm)
            "rain_rate_mm": in_to_mm(raw.get('rrain_piezo')),
            "rain_event_mm": in_to_mm(raw.get('erain_piezo')),
            "rain_hour_mm": in_to_mm(raw.get('hrain_piezo')),
            "rain_24h_mm": in_to_mm(raw.get('last24hrain_piezo')),
            "rain_day_mm": in_to_mm(raw.get('drain_piezo')),
            "rain_week_mm": in_to_mm(raw.get('wrain_piezo')),
            "rain_month_mm": in_to_mm(raw.get('mrain_piezo')),
            "rain_year_mm": in_to_mm(raw.get('yrain_piezo')),
            
            # Sensordaten
            "solar_wm2": float(raw.get('solarradiation', 0.0)),
            "uv": int(raw.get('uv', 0)),
            "vpd": float(raw.get('vpd',