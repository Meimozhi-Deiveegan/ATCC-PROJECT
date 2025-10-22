"""
ATCC Analysis Utilities
- Load multiple daily interval CSVs from `atcc_output/*Traffic_Count_Report_*.csv`
- Compute ADT per category and PCU-converted ADT
- Compute Peak Hour and Peak Hour Factor (PHF) per day using 15-min rows
- Export summary Excel with sheets: ADT, PCU_ADT, PeakHour

Run:
  python atcc_analysis.py --indir atcc_output --pcu '{"2W":0.5,"3W":1.0,"Car":1.0,"LCV":1.5,"Bus":3.0,"Truck":3.0,"Others":1.5,"Pedestrian":0.3}'
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

CATS = ["2W", "3W", "Car", "LCV", "Bus", "Truck", "Others", "Total", "Pedestrian"]


def load_daily_csvs(indir: Path) -> List[pd.DataFrame]:
    files = sorted(indir.glob("**/Traffic_Count_Report_*.csv"))
    out = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df["_source_file"] = f.name
            out.append(df)
        except Exception as e:
            print(f"Skip {f}: {e}")
    return out


def compute_adt(daily_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    # Take Daily Total row from each day
    daily_totals = []
    for df in daily_dfs:
        if df.empty:
            continue
        tot = df[df["Interval"] == "Daily Total"].copy()
        if tot.empty:
            # sum to emulate
            sums = {col: df[col].sum() if col in CATS else None for col in df.columns}
            sums["Interval"] = "Daily Total"
            tot = pd.DataFrame([sums])
        daily_totals.append(tot)
    if not daily_totals:
        return pd.DataFrame()
    cat_cols = [c for c in CATS if c in daily_totals[0].columns]
    stacked = pd.concat(daily_totals, ignore_index=True)
    avg = stacked[cat_cols].mean(numeric_only=True)
    out = pd.DataFrame({"Vehicle Category": cat_cols, "Avg Daily Count": [int(round(avg[c])) for c in cat_cols]})
    return out


def compute_pcu(df_counts: pd.DataFrame, pcu_map: Dict[str, float]) -> pd.DataFrame:
    df = df_counts.copy()
    df["Avg Daily PCU"] = df.apply(lambda r: int(round(r["Avg Daily Count"] * float(pcu_map.get(str(r["Vehicle Category"]), 1.0)))), axis=1)
    return df[["Vehicle Category", "Avg Daily Count", "Avg Daily PCU"]]


def compute_peak_hour_and_phf(df: pd.DataFrame) -> pd.DataFrame:
    # Expect 15-min intervals; derive per-hour sums and 15-min max for PHF
    data = df[df["Interval"] != "Daily Total"].copy()
    # Parse minutes from interval start
    data["start_min"] = data["Interval"].str.slice(0, 5).str.split(":").apply(lambda x: int(x[0]) * 60 + int(x[1]))
    # Total column should exist
    if "Total" not in data.columns:
        data["Total"] = 0
    data = data.sort_values("start_min")

    # Hour buckets
    data["hour"] = data["start_min"] // 60
    hourly = data.groupby("hour")["Total"].sum()

    # Within each hour, compute 15-min max
    phf_rows = []
    for hour, group in data.groupby("hour"):
        hour_total = int(hourly.loc[hour])
        # 15-min max = max of four consecutive 15-min bins in that hour
        max_q = int(group["Total"].max()) if not group.empty else 0
        phf = (max_q * 4 / hour_total) if hour_total > 0 else 0.0
        phf_rows.append({
            "Hour": f"{int(hour):02d}:00-{(int(hour)+1)%24:02d}:00",
            "Hourly Total": hour_total,
            "Highest 15-min Volume": max_q,
            "PHF": round(phf, 3)
        })

    return pd.DataFrame(phf_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="./atcc_output")
    ap.add_argument("--pcu", default='{"2W":0.5,"3W":1.0,"Car":1.0,"LCV":1.5,"Bus":3.0,"Truck":3.0,"Others":1.5,"Pedestrian":0.3}')
    args = ap.parse_args()

    indir = Path(args.indir)
    pcu_map = json.loads(args.pcu)

    daily = load_daily_csvs(indir)
    if not daily:
        print("No daily CSVs found.")
        return

    adt_counts = compute_adt(daily)
    pcu_adt = compute_pcu(adt_counts, pcu_map)

    # Peak hour table for each day
    peak_tables = []
    for df in daily:
        src = df.get("_source_file", ["day"])[0] if isinstance(df.get("_source_file"), pd.Series) else "day"
        phf_df = compute_peak_hour_and_phf(df)
        phf_df.insert(0, "Day", src)
        peak_tables.append(phf_df)

    peak_all = pd.concat(peak_tables, ignore_index=True)

    outxlsx = indir / "ATCC_Weekly_Summary.xlsx"
    with pd.ExcelWriter(outxlsx, engine="openpyxl") as writer:
        adt_counts.to_excel(writer, sheet_name="ADT", index=False)
        pcu_adt.to_excel(writer, sheet_name="PCU_ADT", index=False)
        peak_all.to_excel(writer, sheet_name="PeakHour", index=False)

    print(f"Saved summary: {outxlsx}")


if __name__ == "__main__":
    main()
