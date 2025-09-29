import fastf1
import pandas as pd

# Enable caching to avoid re-downloading
fastf1.Cache.enable_cache("f1_cache")

def get_driver_avg_quali_times(season, round_number):
    try:
        session = fastf1.get_session(season, round_number, 'Q')
        session.load(laps=True, telemetry=False)

        event = session.event  # Access event metadata
        drivers = session.drivers
        results = []

        for drv in drivers:
            laps = session.laps.pick_driver(drv)
            quali_laps = laps[laps['LapTime'].notnull()]

            if quali_laps.empty:
                continue

            avg_time = quali_laps['LapTime'].mean()

            results.append({
                'Season': season,
                'Round': round_number,
                'EventName': event.EventName,
                'Driver': session.get_driver(drv)['Abbreviation'],
                'AvgQualiTime': avg_time.total_seconds()
            })

        return results

    except Exception as e:
        print(f"Error processing {season} round {round_number}: {e}")
        return []

# Collect results for 2023–2025
all_results = []
for season in [2023, 2024, 2025]:
    schedule = fastf1.get_event_schedule(season)
    for rnd in schedule['RoundNumber']:
        all_results.extend(get_driver_avg_quali_times(season, rnd))

df = pd.DataFrame(all_results)

# Save to CSV (optional)
df.to_csv("driver_avg_quali_times_2023_2025.csv", index=False)

print(df.head(20))
