# strava_connection

Export and analysis of Strava activities.

- `data/activities.csv` – 100 activities (2026-06-13 → 2026-11-15) pulled via the Strava MCP connector
- `analyze.py` – sport breakdown, weekly volume, road-run pace trend; writes `output/`

```bash
pip install pandas matplotlib tabulate
python3 analyze.py [data/activities.csv] [output]
```
