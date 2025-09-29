import fastf1
import pandas as pd

# Enable caching so sessions load faster after first call
fastf1.Cache.enable_cache('f1_cache')

# Load your race results
df_results = pd.read_csv('race_results_2023_2024_2025.csv')

def get_avg_pitstop_time(season, round_number, driver_abbr, driver_number):
    try:
        # Load the race session
        session = fastf1.get_session(int(season), int(round_number), 'R')
        session.load()
        
        laps = session.laps

        # First try by Abbreviation
        pitstops = laps[laps['Driver'] == driver_abbr]['PitTime']
        
        # If empty, fall back to DriverNumber
        if pitstops.empty and 'DriverNumber' in laps.columns:
            pitstops = laps[laps['DriverNumber'] == str(driver_number)]['PitTime']
        
        # Return mean if valid
        if pitstops.notnull().any():
            return float(pitstops.mean())
        else:
            return None
    except Exception as e:
        print(f"Error for {season} round {round_number} driver {driver_abbr}: {e}")
        return None

# Compute average pit stop time for each row
df_results['AvgPitStopTime'] = df_results.apply(
    lambda row: get_avg_pitstop_time(
        row['Season'], 
        row['RoundNumber'], 
        row['Abbreviation'], 
        row['DriverNumber']
    ), axis=1
)

# Save updated CSV
df_results.to_csv('race_results_2023_2024_2025_with_pitstops.csv', index=False)