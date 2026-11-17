"""Download (if needed), tidy and analyse the gender pay gap reports; write tables and charts.

    python run_analysis.py           # uses data/processed if present
    python run_analysis.py --rebuild # re-download and rebuild from the raw CSVs
"""
import sys
from pathlib import Path

import pandas as pd

from gpg import analysis as A
from gpg import data, figures

OUT = Path(__file__).resolve().parent / "outputs"


def main(rebuild: bool):
    if rebuild or not data.PROCESSED.exists():
        data.download()
        df = data.build()
    else:
        df = data.load()
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(parents=True, exist_ok=True)

    t = A.trend(df)
    s = A.by_sector(df)
    z = A.by_size(df)
    q = A.quartile_shares(df)
    b = A.binned_relationship(df)
    e = A.what_explains_the_gap(df)
    bonus = A.bonus_summary(df)
    change = A.employer_change(df, 2017, A.LATEST)

    t.to_csv(OUT / "tables" / "trend_by_year.csv", index=False, float_format="%.2f")
    s.to_csv(OUT / "tables" / "gap_by_sector_2025.csv", index=False, float_format="%.2f")
    z.to_csv(OUT / "tables" / "gap_by_size_2025.csv", index=False, float_format="%.2f")
    b.drop(columns="top_vs_bottom_gap").to_csv(OUT / "tables" / "gap_vs_top_quarter_2025.csv",
                                               index=False, float_format="%.2f")
    pd.Series({**e, **bonus,
               "panel_employers": t.attrs["panel_size"],
               "panel_pct_narrowed_2017_2025": 100 * (change < 0).mean(),
               "panel_median_change_pts": change.median()}).to_csv(
        OUT / "tables" / "headline_numbers.csv", header=["value"], float_format="%.3f")

    figures.trend(t, OUT / "figures" / "1_trend.png")
    figures.sectors(s, OUT / "figures" / "2_sectors.png")
    figures.quartiles(q, OUT / "figures" / "3_quartiles.png")
    figures.relationship(b, OUT / "figures" / "4_top_quarter.png")

    print(f"Reports: {len(df):,}  employers: {df['employer_id'].nunique():,}  years: "
          f"{df['year'].min()}-{df['year'].max()}")
    print(t.round(1).to_string(index=False))
    print(s.round(1).to_string(index=False))
    print(z.to_string(index=False))
    print(q.round(1).to_string())
    print({k: round(v, 3) for k, v in {**e, **bonus}.items()})
    print(f"Panel: {t.attrs['panel_size']:,} employers; {100 * (change < 0).mean():.1f}% narrowed; "
          f"median change {change.median():.2f} pts")


if __name__ == "__main__":
    main("--rebuild" in sys.argv)
