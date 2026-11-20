"""Analyze exported Strava activities: weekly volume, sport breakdown, run pace trend."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/activities.csv")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "output")
out.mkdir(exist_ok=True)

df = pd.read_csv(src, parse_dates=["start_local"])
df["hours"] = df.moving_s / 3600
df["week"] = df.start_local.dt.to_period("W-SUN").dt.start_time

# --- Sport breakdown
by_sport = df.groupby("sport_type").agg(
    n=("id", "count"), km=("distance_km", "sum"), hours=("hours", "sum"),
    elev_m=("elevation_m", "sum"), kcal=("calories", "sum"),
).sort_values("hours", ascending=False).round(1)

# --- Weekly totals
weekly = df.groupby("week").agg(
    n=("id", "count"), hours=("hours", "sum"), elev_m=("elevation_m", "sum"),
    effort=("relative_effort", "sum"),
).round(1)
run_km = df[df.sport_type.isin(["Run", "TrailRun"])].groupby("week").distance_km.sum()
weekly["run_km"] = run_km.reindex(weekly.index).fillna(0).round(1)
weekly = weekly.reindex(pd.date_range(weekly.index.min(), weekly.index.max(), freq="W-MON"), fill_value=0)

# --- Road-run pace trend (flat runs only)
runs = df[df.sport_type == "Run"].copy()
runs["pace_min_km"] = runs.moving_s / 60 / runs.distance_km

# --- Charts
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(weekly.index, weekly.hours, width=5)
ax.set(title="Weekly training hours (all sports)", ylabel="hours")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(out / "weekly_hours.png", dpi=120)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(weekly.index, weekly.run_km, width=5, color="tab:green")
ax.set(title="Weekly running distance (Run + TrailRun)", ylabel="km")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(out / "weekly_run_km.png", dpi=120)

fig, ax = plt.subplots(figsize=(10, 4))
ax.scatter(runs.start_local, runs.pace_min_km, s=runs.distance_km * 8, alpha=.6)
roll = runs.set_index("start_local").pace_min_km.rolling("28D").mean()
ax.plot(roll.index, roll.values, color="tab:red", label="28-day rolling mean")
ax.invert_yaxis(); ax.legend()
ax.set(title="Road run pace (lower = faster)", ylabel="min/km")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(out / "run_pace.png", dpi=120)

# --- Report
md = [f"# Strava summary\n\n{df.start_local.min():%Y-%m-%d} to {df.start_local.max():%Y-%m-%d} — {len(df)} activities, "
      f"{df.hours.sum():.0f} h, {df.distance_km.sum():.0f} km, {df.elevation_m.sum():.0f} m climbed\n",
      "## By sport\n", by_sport.to_markdown(), "\n\n## Weekly\n", weekly.to_markdown(), "\n",
      "\n![](weekly_hours.png)\n![](weekly_run_km.png)\n![](run_pace.png)\n"]
(out / "report.md").write_text("\n".join(md))
print("\n".join(md[:4]))
print("\nBest weeks by hours:\n", weekly.sort_values("hours", ascending=False).head(3))
print("\nRoad run pace: first 5 avg %.2f, last 5 avg %.2f min/km" % (
    runs.sort_values("start_local").pace_min_km.head(5).mean(),
    runs.sort_values("start_local").pace_min_km.tail(5).mean()))
