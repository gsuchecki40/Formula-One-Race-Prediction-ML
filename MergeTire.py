import pandas as pd
import fastf1

fastf1.Cache.enable_cache("f1_cache")  # wherever you want the cache

def tire_proportions_for_race(season: int, round_number: int) -> pd.DataFrame:
    """
    Compute per-driver proportion of laps on each compound for a single race.
    Returns columns: Season, Round, Driver, SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    """
    try:
        session = fastf1.get_session(season, round_number, 'R')
        session.load()  # populates session.laps
        laps = session.laps

        if laps.empty:
            return pd.DataFrame()

        # Build stint lengths the documented way:
        # group by Driver, Stint, Compound and count laps in each stint
        stint_lengths = (
            laps[['Driver', 'Stint', 'Compound', 'LapNumber']]
            .dropna(subset=['Stint', 'Compound'])
            .groupby(['Driver', 'Stint', 'Compound'], as_index=False)['LapNumber']
            .count()
            .rename(columns={'LapNumber': 'StintLength'})
        )

        # Sum across multiple stints of the same compound (e.g., two Medium stints)
        comp_lengths = (
            stint_lengths
            .groupby(['Driver', 'Compound'], as_index=False)['StintLength']
            .sum()
        )

        # Total laps per driver (DNFs will just have fewer laps, which is fine)
        totals = (
            comp_lengths.groupby('Driver', as_index=False)['StintLength']
            .sum()
            .rename(columns={'StintLength': 'TotalLaps'})
        )

        comp_lengths = comp_lengths.merge(totals, on='Driver', how='left')
        comp_lengths['Proportion'] = comp_lengths['StintLength'] / comp_lengths['TotalLaps']

        # Pivot to columns per compound
        tire_df = comp_lengths.pivot(index='Driver', columns='Compound', values='Proportion').reset_index()

        # Ensure a consistent set of columns, fill missing with 0
        for comp in ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']:
            if comp not in tire_df.columns:
                tire_df[comp] = 0.0
        tire_df = tire_df[['Driver', 'SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']].fillna(0.0)

        tire_df['Season'] = season
        tire_df['Round'] = round_number

        return tire_df[['Season', 'Round', 'Driver', 'SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']]

    except Exception as e:
        print(f"Failed {season} Round {round_number}: {e}")
        return pd.DataFrame()

def append_tire_data(main_df: pd.DataFrame) -> pd.DataFrame:
    """
    Loop over unique (Season, Round) pairs in main_df,
    compute tire proportions, and merge back on Abbreviation ↔ Driver.
    """
    out = []
    races = main_df[['Season', 'Round']].drop_duplicates()

    for _, r in races.iterrows():
        season, rnd = int(r['Season']), int(r['Round'])
        tp = tire_proportions_for_race(season, rnd)
        if not tp.empty:
            out.append(tp)

    if not out:
        return main_df.copy()

    tire_data = pd.concat(out, ignore_index=True)

    merged = main_df.merge(
        tire_data,
        left_on=['Season', 'Round', 'Abbreviation'],
        right_on=['Season', 'Round', 'Driver'],
        how='left'
    )

    # If a driver/race didn’t load, fill proportions with 0 so models don’t crash
    for comp in ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']:
        if comp in merged.columns:
            merged[comp] = merged[comp].fillna(0.0)

    return merged

# Example usage with your uploaded CSV
df = pd.read_csv("Processed_F1_Results.csv")
final_df = append_tire_data(df)
final_df.to_csv("F1_with_TireProportions.csv", index=False)
