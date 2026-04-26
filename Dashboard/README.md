Dieses Grafana-Dashboard bietet eine umfassende Visualisierung der Daten einer **Ecowitt Wetterstation**, die in einer **InfluxDB (v2)** gespeichert sind. Die Konfiguration ist hochgradig modular aufgebaut und nutzt moderne Grafana-Features (v13.x) zur Darstellung meteorologischer Metriken.

Hier ist eine strukturierte Beschreibung für dein GitHub-Projekt:

---

# Ecowitt Wetterstation Dashboard für Grafana

Dieses Dashboard ermöglicht eine detaillierte Überwachung und Analyse deiner Wetterdaten. Es ist speziell für die Nutzung mit dem **Ecowitt Exporter** und einer **InfluxDB** Zeitreihendatenbank optimiert.

## 📊 Dashboard Features

Das Dashboard ist in logische Sektionen unterteilt, um sowohl aktuelle Zustände als auch historische Trends (standardmäßig die letzten 24 Stunden) auf einen Blick zu erfassen.

### 1. Aktuelle Wetterlage (Übersicht)
Schnellansicht der wichtigsten Parameter als Stat-Panels:
* **Temperatur & Luftfeuchtigkeit:** Aktuelle Außenwerte inklusive Trends.
* **Luftdruck:** Relativer Luftdruck in hPa.
* **Wind & Regen:** Aktuelle Windgeschwindigkeit und momentane Regenrate ($mm/h$).
* **Sonneneinstrahlung:** Lichtintensität in $W/m^2$.

### 2. Statistiken (24h Highlights)
Zusammenfassung der Extremwerte des vergangenen Tages:
* Höchst- und Tiefsttemperaturen.
* Maximale Windgeschwindigkeiten und stärkste Böen.
* Integrierte **Uhrzeit- und Datumsanzeige** (optimiert für Kiosk-Modus/Wand-Tablets).

### 3. Detaillierte Analysen
* **Temperaturverlauf:** Vergleich von Innen- und Außentemperatur sowie Luftfeuchtigkeit in kombinierten Zeitreihendiagrammen.
* **Niederschlag:** Detaillierte Aufschlüsselung der Regenmengen (Event, Stunde, Tag, Woche, Monat, Jahr) in einer übersichtlichen Tabelle und Grafik.
* **Wind-Monitoring:** * Kombinierte Anzeige von Windgeschwindigkeit und Böen.
    * **Beaufort-Skala:** Visualisierung der Windstärke nach dem Beaufort-System.
    * **Windrichtung:** Anzeige der Richtung sowohl als Zeitreihe (Grad) als auch durch intuitive Richtungssymbole (Pfeile).
* **Sonne & UV:** * **UV-Index:** Gauge-Panel mit Risikobewertung (Niedrig bis Extrem).
    * **Solar-Heatmap:** Visualisierung der Sonneneinstrahlung über den Zeitverlauf.

## 🛠 Technische Details

* **Datenquelle:** InfluxDB v2 (Flux Query Language).
* **Bucket-Name:** `wetterstation` (standardmäßig im JSON konfiguriert).
* **Grafana Version:** Optimiert für Grafana **v13.0.1** oder neuer.
* **Einheiten:** Vollständig metrisches System (Celsius, km/h, mm, hPa).

## 🚀 Installation

1.  Stelle sicher, dass deine Wetterdaten in einer InfluxDB im Bucket `wetterstation` unter dem Measurement `weather_station` gespeichert werden.
2.  Importiere die `Grafana-Dashboard.json` in deine Grafana-Instanz.
3.  Passen ggf. die Datenquelle (`uid: influxdb`) an deine lokale Konfiguration an.

## 📱 Design & Layout
Das Layout nutzt ein responsives Grid, das besonders gut auf Desktop-Monitoren und größeren Tablets zur Geltung kommt. Die Panels verwenden farbliche Schwellenwerte (Thresholds), um kritische Wetterereignisse (z. B. Sturm oder hohe UV-Strahlung) sofort optisch zu signalisieren.

---

### Key-Metriken im JSON (Auszug):
| Feld | Beschreibung | Einheit |
| :--- | :--- | :--- |
| `temp_out_c` | Außentemperatur | °C |
| `wind_speed_kmh` | Windgeschwindigkeit | km/h |
| `rain_day_mm` | Tagesniederschlag | mm |
| `uv` | UV-Index | Index (0-12) |
| `solar_wm2` | Sonneneinstrahlung | $W/m^2$ |
