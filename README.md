# Ecowitt → InfluxDB2

Kleiner Flask-Dienst, der die Datenpakete einer Ecowitt-Wetterstation
(Customized-Upload, Ecowitt-Protokoll) entgegennimmt, in metrische Einheiten
umrechnet und in InfluxDB 2.x schreibt. Getestet mit Konsole HP2564AE und
Außensensor WS90 (Piezo-Regenmesser).

## 1. Voraussetzungen

* Linux-Server mit systemd, Python 3, InfluxDB 2.x
* Python-Pakete: `pip3 install flask influxdb-client` (Debian: `apt install python3-flask python3-influxdb-client`)
* Die Konsole muss den Server erreichen (gleiches Netz oder VPN)

## 2. Dateien

| Datei | Zweck |
|---|---|
| `ecowitt_to_influxdb.py` | Empfänger |
| `config.env.example` | Vorlage für `/etc/ecowitt/config.env` |
| `ecowitt.service` | systemd-Unit |
| `tools/umtaggen.py` | Altdaten von versioniertem auf neuen `model`-Tag umtaggen (siehe Abschnitt 8) |
| `Dashboard/` | Grafana-Dashboard |

## 3. Installation

```bash
sudo mkdir -p /opt/ecowitt /etc/ecowitt
sudo cp ecowitt_to_influxdb.py /opt/ecowitt/
sudo cp config.env.example /etc/ecowitt/config.env
sudo chown root:<dienstuser> /etc/ecowitt/config.env
sudo chmod 640 /etc/ecowitt/config.env
sudo nano /etc/ecowitt/config.env          # Passkey und Token eintragen
sudo cp ecowitt.service /etc/systemd/system/   # User= anpassen
sudo systemctl daemon-reload
sudo systemctl enable --now ecowitt.service
```

Die Konfiguration kommt ausschließlich aus Umgebungsvariablen, die systemd
per `EnvironmentFile` lädt:

| Variable | Pflicht | Standard |
|---|---|---|
| `ECOWITT_PASSKEY` | ja | – |
| `INFLUX_TOKEN` | ja | – |
| `ECOWITT_HOST` | nein | `0.0.0.0` (alle Schnittstellen); z. B. die VPN-IP, damit der Port nicht öffentlich erreichbar ist |
| `ECOWITT_PORT` | nein | `8090` |
| `ECOWITT_DEBUG` | nein | `false` |
| `INFLUX_URL` | nein | `http://localhost:8086` |
| `INFLUX_ORG` | nein | `Bergkoppel` |
| `INFLUX_BUCKET` | nein | `wetterstation` |

Bei `ECOWITT_HOST` mit einer VPN-IP in `ecowitt.service` `After=`/`Wants=`
um die VPN-Unit ergänzen (z. B. `wg-quick@wg0.service`), sonst scheitert
der Start beim Booten, bis die Schnittstelle da ist.

Ein manueller Start ohne exportierte Variablen bricht mit
„Fehlende Umgebungsvariable" ab.

## 4. Passkey

Der Passkey ist der MD5-Wert der MAC-Adresse der Konsole, in
Großbuchstaben und mit Doppelpunkten:

```bash
echo -n "AA:BB:CC:DD:EE:FF" | md5sum | tr a-f A-F
```

Die MAC zeigt die WS View Plus App oder `curl http://<konsole>/get_network_info`.
Der Dienst gibt den Passkey nie aus, auch nicht im Debug-Modus. Pakete mit
falschem Passkey werden mit 401 abgewiesen und als
`Abgewiesen: falscher oder fehlender PASSKEY` geloggt.

## 5. Konsole einrichten (WS View Plus)

Others → Customized → Protokoll **Ecowitt**, Server-IP des Servers, Pfad
`/data/report/`, Port `8090`, Intervall `16` s.

## 6. Journal

```bash
journalctl -u ecowitt.service -f -o cat
```

* Pro Paket eine Zugriffszeile mit `200`.
* Beim Start und bei jeder Änderung: `Konsole: <Modell> <Version> (<Firmware>)`,
  die Liste der Rohfeldnamen (ohne Werte), nicht gespeicherte und fehlende
  Rohfelder. So fällt nach einem Firmware-Update sofort auf, wenn Felder
  hinzukommen oder umbenannt werden.
* Mit `ECOWITT_DEBUG=true` zusätzlich jedes Paket mit allen Rohwerten (ohne PASSKEY).

## 7. Datenmodell

Measurement `weather_station`, Tag `model` = Modell ohne Version
(z. B. `HP2564AE_Pro`). Die Version steht nur im Journal, damit ein
Firmware-Update keine neue Serie erzeugt.

| Feld | Rohfeld | Einheit |
|---|---|---|
| `temp_in_c`, `temp_out_c` | `tempinf`, `tempf` | °C |
| `hum_in`, `hum_out` | `humidityin`, `humidity` | % |
| `press_rel_hpa`, `press_abs_hpa` | `baromrelin`, `baromabsin` | hPa |
| `wind_dir`, `wind_dir_avg10m` | `winddir`, `winddir_avg10m` | ° |
| `wind_speed_kmh`, `wind_gust_kmh`, `wind_max_daily_kmh` | `windspeedmph`, `windgustmph`, `maxdailygust` | km/h |
| `wind_bft` | aus `wind_speed_kmh` | Beaufort |
| `rain_rate_mm` | `rrain_piezo` | mm/h |
| `rain_event_mm`, `rain_hour_mm`, `rain_24h_mm`, `rain_day_mm`, `rain_week_mm`, `rain_month_mm`, `rain_year_mm` | `erain_piezo`, `hrain_piezo`, `last24hrain_piezo`, `drain_piezo`, `wrain_piezo`, `mrain_piezo`, `yrain_piezo` | mm |
| `rain_state` | `srain_piezo` | 0/1, 1 = Piezo-Fläche nass (bleibt bis zum Abtrocknen bzw. 2 h ohne Änderung) |
| `solar_wm2`, `uv`, `vpd` | `solarradiation`, `uv`, `vpd` | W/m², Index, kPa |
| `batt_volt`, `cap_volt` | `wh90batt`, `ws90cap_volt` | V |

Fehlende Rohfelder werden als 0 gespeichert. `srain_piezo` liefert die
Konsole ab Firmware EasyWeatherPro V5.2.7 (HP2564AE_Pro V2.1.4).

## 8. Umstieg von älteren Versionen

Bis Oktober 2026 enthielt der Tag `model` die Version
(`HP2564AE_Pro_V2.0.9`), jedes Firmware-Update erzeugte also eine neue
Serie. Flux hängt Serien mit verschiedenen Tag-Werten nach Tag-Namen
hintereinander statt nach Zeit, sodass `last()`/`first()` über mehrere
Serien falsche Werte liefern. Außerdem greifen Grafana-Overrides auf
Seriennamen wie `temp_out_c HP2564AE_Pro_V2.0.9` dann nicht mehr.

`tools/umtaggen.py` kopiert die Altdaten mit neuem Tag, prüft Anzahl und
Summe je Feld und Woche und löscht danach die alten Serien:

```bash
set -a; . /etc/ecowitt/config.env; set +a
python3 tools/umtaggen.py export   # Line Protocol nach ~/ecowitt-umtaggen/ (Rückweg)
python3 tools/umtaggen.py copy
python3 tools/umtaggen.py verify   # muss "VERIFY OK" melden
python3 tools/umtaggen.py delete
```

Die Konstanten `OLD`, `NEW`, `START` und `CUT` oben im Skript vorher anpassen.
Die alte `ecowitt.conf` wird nicht mehr gelesen; ihre Werte gehören in
`/etc/ecowitt/config.env`.
