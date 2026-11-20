"""Build a static dashboard (index.html) from data/activities.csv for Vercel."""
import json
from pathlib import Path

import pandas as pd

df = pd.read_csv("data/activities.csv", parse_dates=["start_local"])
df["hours"] = df.moving_s / 3600
df["week"] = df.start_local.dt.to_period("W-SUN").dt.start_time
weeks = pd.date_range(df.week.min(), df.week.max(), freq="W-MON")
wk = df.groupby("week").hours.sum().reindex(weeks, fill_value=0).round(2)
rk = (df[df.sport_type.isin(["Run", "TrailRun"])].groupby("week").distance_km.sum()
      .reindex(weeks, fill_value=0).round(1))
sp = df.groupby("sport_type").hours.sum().sort_values(ascending=False).round(1)
runs = df[df.sport_type == "Run"].sort_values("start_local")
data = {
    "weeks": [d.strftime("%Y-%m-%d") for d in weeks], "hours": wk.tolist(), "runKm": rk.tolist(),
    "sports": sp.index.tolist(), "sportHours": sp.tolist(),
    "runDates": runs.start_local.dt.strftime("%Y-%m-%d").tolist(),
    "runPace": (runs.moving_s / 60 / runs.distance_km).round(2).tolist(),
}
tot = {"n": len(df), "h": round(df.hours.sum()), "km": round(df.distance_km.sum()), "elev": round(df.elevation_m.sum())}
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Strava Connection</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:16px;background:#fff;color:#111}}
.k{{display:flex;gap:12px;flex-wrap:wrap}}.k div{{flex:1;min-width:120px;padding:12px;border:1px solid #ddd;border-radius:8px}}
.k b{{display:block;font-size:1.6em}}@media(prefers-color-scheme:dark){{body{{background:#111;color:#eee}}.k div{{border-color:#444}}}}</style>
</head><body><h1>Training dashboard</h1>
<div class="k"><div><b>{tot['n']}</b>activities</div><div><b>{tot['h']} h</b>moving time</div>
<div><b>{tot['km']} km</b>distance</div><div><b>{tot['elev']} m</b>climbed</div></div>
<h2>Weekly hours</h2><canvas id="a"></canvas><h2>Weekly running km</h2><canvas id="b"></canvas>
<h2>Hours by sport</h2><canvas id="c"></canvas><h2>Road run pace (min/km)</h2><canvas id="d"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>const D={json.dumps(data)};
new Chart(a,{{type:'bar',data:{{labels:D.weeks,datasets:[{{label:'hours',data:D.hours}}]}}}});
new Chart(b,{{type:'bar',data:{{labels:D.weeks,datasets:[{{label:'km',data:D.runKm,backgroundColor:'#2a9d4a'}}]}}}});
new Chart(c,{{type:'bar',data:{{labels:D.sports,datasets:[{{label:'hours',data:D.sportHours}}]}},options:{{indexAxis:'y'}}}});
new Chart(d,{{type:'line',data:{{labels:D.runDates,datasets:[{{label:'min/km',data:D.runPace,borderColor:'#e63946'}}]}},options:{{scales:{{y:{{reverse:true}}}}}}}});
</script></body></html>"""

# --- Peaks section + map
from html import escape
pk = json.loads(Path("data/summits.json").read_text())
summits = sorted((x for x in pk if x["kind"] == "summit"), key=lambda x: x["date"], reverse=True)
rows = "".join(
    f"<tr><td>{escape(x['name'])}</td><td>{x['elev'] or '–'}</td><td>{x['date']}</td><td>{x['sport']}</td><td>{x['conf']}</td></tr>"
    for x in summits)
peaks = (f"<h2>Summits ({len(summits)})</h2><p><a href='map.html'>Open the summit map</a>. Identified from the GPS high point of each "
         "activity; peaks marked low/medium confidence are best guesses.</p>"
         "<table><thead><tr><th>Peak</th><th>m</th><th>Date</th><th>Type</th><th>Confidence</th></tr></thead>"
         f"<tbody>{rows}</tbody></table>"
         "<style>table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:4px 8px;border-bottom:1px solid #8884}</style>")
html = html.replace("</body></html>", peaks + "</body></html>")
Path("index.html").write_text(html)

mapjs = json.dumps(pk)
Path("map.html").write_text("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Summit map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body{height:100%;margin:0;font-family:system-ui,sans-serif}#m{height:100%}
.l{position:absolute;z-index:1000;top:10px;right:10px;background:#fffd;color:#111;padding:8px 10px;border-radius:6px;font-size:13px}
.l a{color:#06c}</style></head><body><div id="m"></div>
<div class="l"><b>Summits</b><br><span style="color:#d62828">&#9679;</span> identified peak<br>
<span style="color:#888">&#9679;</span> unidentified high point<br><span style="color:#f77f00">&#9679;</span> turned back<br>
<a href="./">&larr; dashboard</a></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>const P=""" + mapjs + """;
const map=L.map('m');L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:17,
attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
const col={summit:'#d62828',unidentified:'#888',turnback:'#f77f00'};
const b=[];P.forEach(p=>{const m=L.circleMarker([p.lat,p.lon],{radius:p.kind==='summit'?8:5,color:'#fff',weight:1.5,
fillColor:col[p.kind],fillOpacity:.9}).addTo(map);
const e=p.elev?p.elev+' m':'GPS high point '+p.gps_elev+' m';
m.bindPopup('<b>'+p.name+'</b><br>'+e+'<br>'+p.date+' &middot; '+p.sport+'<br>confidence: '+p.conf+(p.note?'<br>'+p.note:''));
b.push([p.lat,p.lon]);});map.fitBounds(b,{padding:[30,30]});</script></body></html>""")
print("wrote index.html and map.html")
