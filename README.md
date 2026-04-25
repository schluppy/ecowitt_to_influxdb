***

# SOP: Ecowitt-to-InfluxDB Bridge

Diese Anleitung beschreibt die Installation und den Betrieb einer Python-basierten Bridge, die Wetterdaten von Ecowitt-Stationen (im Ecowitt-Protokoll) empfängt, in das metrische System umrechnet und in eine InfluxDB 2.x schreibt.

## 1. Voraussetzungen

* **Hardware:** Ein ständig laufender Server (z. B. Raspberry Pi, Ubuntu-Server/OptiPlex).
* **Software:** Python 3.x, InfluxDB 2.x.
* **Netzwerk:** Die Wetterstation und der Server müssen sich im selben Netzwerk befinden.

## 2. Installation der Abhängigkeiten

Installiere die benötigten Python-Bibliotheken:

```bash
pip3 install flask influxdb-client configparser
```

## 3. Dateistruktur

Erstelle ein Verzeichnis für das Skript (z. B. `~/ecowitt-direct`) und lege dort zwei Dateien an:

1.  `ecowitt_bridge.py` (Das Python-Skript)
2.  `ecowitt.conf` (Die Konfigurationsdatei)

### ecowitt.conf Beispiel
```ini
[influxdb]
url = http://localhost:8086
token = DEIN_INFLUX_TOKEN
org = DEINE_ORG
bucket = wetterstation

[server]
port = 8090
passkey = NONE

[settings]
debug = True
```

## 4. Einrichtung des Systemd-Service

Um sicherzustellen, dass das Skript nach einem Neustart automatisch startet, wird ein Linux-Service erstellt.

1.  Erstelle die Service-Datei:
    ```bash
    sudo nano /etc/systemd/system/ecowitt.service
    ```

2.  Füge folgenden Inhalt ein (Pfade und User anpassen!):
    ```ini
    [Unit]
    Description=Ecowitt InfluxDB Bridge
    After=network.target

    [Service]
    # Wichtig für sofortige Log-Ausgabe
    Environment=PYTHONUNBUFFERED=1
    ExecStart=/usr/bin/python3 /home/deinuser/ecowitt-direct/ecowitt_bridge.py
    WorkingDirectory=/home/deinuser/ecowitt-direct
    Restart=always
    User=deinuser

    [Install]
    WantedBy=multi-user.target
    ```

3.  Service aktivieren und starten:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable ecowitt.service
    sudo systemctl start ecowitt.service
    ```

## 5. Konfiguration der Wetterstation (WS View Plus App)

1.  Öffne die **WS View Plus** App.
2.  Wähle deine Station aus und gehe zu **Others -> Customized**.
3.  Wähle das Protokoll: **Ecowitt**.
4.  Server IP: Die IP deines Linux-Servers.
5.  Path: `/data/report/`
6.  Port: `8090`
7.  Interval: `16` (oder gewünschter Wert).

## 6. Ermittlung des Passkeys (Lern-Modus)

1.  Stelle sicher, dass in der `ecowitt.conf` steht: `passkey = NONE`.
2.  Überprüfe die Logs:
    ```bash
    sudo journalctl -u ecowitt.service -f -o cat
    ```
3.  Sobald Daten empfangen werden, erscheint eine Meldung:
    `LERN-MODUS AKTIV! Empfangener PASSKEY: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
4.  Kopiere diesen Key in deine `ecowitt.conf`.
5.  Starte den Service neu: `sudo systemctl restart ecowitt.service`.

## 7. Datenfelder in InfluxDB

Das Skript konvertiert automatisch folgende Werte:
* **Temperatur:** Fahrenheit (°F) -> Celsius (°C)
* **Luftdruck:** inHg -> hPa
* **Windgeschwindigkeit:** mph -> kmh + Beaufort (Bft)
* **Niederschlag:** inch -> mm

***
