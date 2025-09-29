import pandas as pd
import numpy as np

def process_f1_results(file_path: str, sheet_name: str = "Sheet1"):
    # Load
df = pd.read_csv('~/Desktop/Desktop`/ALLMerged.csv', sheet_name=sheet_name)

    # Parse the Time column into seconds
    def parse_time_to_seconds(time_str):
        try:
            td = pd.to_timedelta(time_str)
            return td.total_seconds()
        except Exception:
            return np.nan

    df['ParsedTime_s'] = df['Time'].apply(parse_time_to_seconds)

    # Work race by race (Season + Round)
    results = []
    for (season, rnd), group in df.groupby(['Season', 'Round']):
        group = group.sort_values(by="Position").copy()

        # First car's ParsedTime_s is usually a full duration
        leader_time = group.iloc[0]['ParsedTime_s']

        # If leader_time is valid, use it as reference
        if pd.notnull(leader_time) and leader_time > 1000:  # sanity check (~>15 min)
            total_times = [leader_time]
            for i in range(1, len(group)):
                t = group.iloc[i]['ParsedTime_s']
                # If t is small (< leader_time/2), treat as gap to leader
                if pd.notnull(t) and t < leader_time / 2:
                    total_times.append(leader_time + t)
                else:
                    total_times.append(t)
            group['FinishTime_s'] = total_times
        else:
            # fallback: just use parsed time
            group['FinishTime_s'] = group['ParsedTime_s']

        # Gap to car ahead
        group['DeltaFromAhead_s'] = group['FinishTime_s'].diff().fillna(0)

        # Deviation from race average
        avg_time = group['FinishTime_s'].mean()
        group['DeviationFromAvg_s'] = group['FinishTime_s'] - avg_time

        results.append(group)

    df_out = pd.concat(results).reset_index(drop=True)

    return df_out