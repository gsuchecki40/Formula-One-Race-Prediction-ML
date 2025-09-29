import pandas as pd

# Input files
RACE_FILE = "race_results_2023_2024_2025_with_pitstops.csv"
QUALI_FILE = "QualiTimes.csv"
WEATHER_FILE = "f1_avg_weather_2023_2025.csv"

# Output file
OUTPUT_FILE = "f1_merged_quali_race_weather_2023_2025.csv"


def main():
    # Read inputs
    race = pd.read_csv(RACE_FILE)
    quali = pd.read_csv(QUALI_FILE)
    weather = pd.read_csv(WEATHER_FILE)

    # Normalize key columns
    # Race: keys are Season (year), RoundNumber (round), Abbreviation (driver code)
    race = race.copy()
    race.rename(columns={"RoundNumber": "Round"}, inplace=True)

    # Quali: keys are Season, Round, Driver (driver code)
    quali = quali.copy()

    # Weather: keys are Year, Round
    weather = weather.copy()
    weather.rename(columns={"Year": "Season"}, inplace=True)

    # Merge quali times onto race results by Season+Round+Driver code
    merged = race.merge(
        quali[["Season", "Round", "Driver", "AvgQualiTime"]],
        left_on=["Season", "Round", "Abbreviation"],
        right_on=["Season", "Round", "Driver"],
        how="left",
    )

    # Drop the helper column 'Driver' introduced from quali
    if "Driver" in merged.columns:
        merged.drop(columns=["Driver"], inplace=True)

    # Merge weather by Season+Round (weather applies to all drivers in that event)
    merged = merged.merge(
        weather,
        on=["Season", "Round"],
        how="left",
        suffixes=("", "_weather"),
    )

    # Write output
    merged.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote merged file: {OUTPUT_FILE}")
    print(f"Rows: {len(merged):,}; Columns: {len(merged.columns)}")


if __name__ == "__main__":
    main()

