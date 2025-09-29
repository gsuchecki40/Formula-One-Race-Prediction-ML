import fastf1
import pandas as pd

years = [2023, 2024, 2025]
all_results = []

for year in years:
    try:
        schedule = fastf1.get_event_schedule(year)
    except Exception as e:
        print(f"Failed to load schedule data for {year}: {e}")
        continue
    for _, race in schedule.iterrows():
        try:
            session = fastf1.get_session(year, race['RoundNumber'], 'R')
            session.load()
            results = session.results.copy()
            results['Season'] = year
            results['RoundNumber'] = race['RoundNumber']
            all_results.append(results)
        except Exception as e:
            print(f"Skipping round {race['RoundNumber']} {year} due to error: {e}")

# Combine all results into one DataFrame
if all_results:
    combined_results = pd.concat(all_results, ignore_index=True)
    combined_results.to_csv('race_results_2023_2024_2025.csv', index=False)
    print("CSV file saved as race_results_2023_2024_2025.csv")
else:
    print("No race results collected.")