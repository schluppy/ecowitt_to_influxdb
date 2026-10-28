#!/usr/bin/env python3
# Alte Serien model=HP2564AE_Pro_V* auf model=HP2564AE_Pro umtaggen.
# Aufruf auf dem Server mit geladener /etc/ecowitt/config.env:
#   python3 umtaggen.py export   -> ~/ecowitt-umtaggen/alt-<woche>.lp.gz (Line Protocol, Rückweg)
#   python3 umtaggen.py copy     -> Kopie mit neuem Tag in denselben Bucket
#   python3 umtaggen.py verify   -> Anzahl + Summe je Feld und Woche alt vs. neu
#   python3 umtaggen.py delete   -> alte Serien löschen (nur nach verify OK)
import datetime as dt, gzip, os, sys
from influxdb_client import InfluxDBClient

e = os.environ
cl = InfluxDBClient(url=e["INFLUX_URL"], token=e["INFLUX_TOKEN"], org=e["INFLUX_ORG"], timeout=600_000)
q = cl.query_api(); B = e["INFLUX_BUCKET"]; ORG = e["INFLUX_ORG"]
NEW = "HP2564AE_Pro"
OLD = ["HP2564AE_Pro_V2.0.9", "HP2564AE_Pro_V2.1.4"]
START = dt.datetime(2026, 7, 13, tzinfo=dt.timezone.utc)      # vor Inbetriebnahme 20.07.
CUT = dt.datetime(2026, 10, 28, 12, 43, 45, tzinfo=dt.timezone.utc)  # Umschaltung neues Skript
OUT = os.path.expanduser("~/ecowitt-umtaggen")
OLD_FILTER = " or ".join(f'r.model == "{m}"' for m in OLD)

def weeks():
    s = START
    while s < CUT:
        t = min(s + dt.timedelta(days=7), CUT)
        yield s, t
        s = t

def iso(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def export():
    os.makedirs(OUT, mode=0o700, exist_ok=True)
    for s, t in weeks():
        flux = (f'from(bucket:"{B}") |> range(start:{iso(s)}, stop:{iso(t)}) '
                f'|> filter(fn:(r)=> r._measurement=="weather_station" and ({OLD_FILTER}))')
        n = 0
        with gzip.open(f"{OUT}/alt-{s:%Y%m%d}.lp.gz", "wt") as f:
            for r in q.query_stream(flux):
                v = r.get_value()
                if isinstance(v, bool): val = "true" if v else "false"
                elif isinstance(v, int): val = f"{v}i"
                elif isinstance(v, float): val = repr(v)
                else: val = '"' + str(v).replace('"', '\\"') + '"'
                ns = int(r.get_time().timestamp()) * 1_000_000_000 + r.get_time().microsecond * 1000
                f.write(f'weather_station,model={r.values["model"]} {r.get_field()}={val} {ns}\n')
                n += 1
        print(f"export {s:%Y-%m-%d}: {n} Punkte", flush=True)

def copy():
    for s, t in weeks():
        flux = (f'from(bucket:"{B}") |> range(start:{iso(s)}, stop:{iso(t)}) '
                f'|> filter(fn:(r)=> r._measurement=="weather_station" and ({OLD_FILTER})) '
                f'|> map(fn:(r)=> ({{r with model: "{NEW}"}})) '
                f'|> to(bucket:"{B}", org:"{ORG}", tagColumns:["model"]) |> count()')
        n = sum(r.get_value() for tbl in q.query(flux) for r in tbl.records)
        print(f"copy {s:%Y-%m-%d}: {n} Punkte geschrieben", flush=True)

def agg(s, t, cond, fn):
    flux = (f'from(bucket:"{B}") |> range(start:{iso(s)}, stop:{iso(t)}) '
            f'|> filter(fn:(r)=> r._measurement=="weather_station" and ({cond})) '
            f'|> toFloat() |> group(columns:["_field"]) |> {fn}()')
    return {r.get_field(): r.get_value() for tbl in q.query(flux) for r in tbl.records}

def verify():
    ok = True
    for s, t in weeks():
        for fn in ("count", "sum"):
            a = agg(s, t, OLD_FILTER, fn); b = agg(s, t, f'r.model == "{NEW}"', fn)
            bad = [f for f in set(a) | set(b) if abs((a.get(f) or 0) - (b.get(f) or 0)) > 1e-6 * max(1, abs(a.get(f) or 0))]
            if bad:
                ok = False
                print(f"ABWEICHUNG {s:%Y-%m-%d} {fn}: {[(f, a.get(f), b.get(f)) for f in bad]}")
        print(f"verify {s:%Y-%m-%d}: {sum(agg(s, t, OLD_FILTER, 'count').values())} alt", flush=True)
    print("VERIFY OK" if ok else "VERIFY FEHLER")

def delete():
    d = cl.delete_api()
    for m in OLD:
        d.delete(START, dt.datetime.now(dt.timezone.utc), f'_measurement="weather_station" AND model="{m}"', bucket=B, org=ORG)
        print(f"geloescht: {m}", flush=True)

{"export": export, "copy": copy, "verify": verify, "delete": delete}[sys.argv[1]]()
