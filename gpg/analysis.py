"""The questions this project answers, one function each."""
import numpy as np
import pandas as pd

LATEST = 2025
MIN_SECTOR_EMPLOYERS = 50  # sectors with fewer reporting employers are too small to compare


def latest_names(df: pd.DataFrame) -> pd.Series:
    """Most recent name for each employer ID (employers rename over time)."""
    return df.sort_values("year").groupby("employer_id")["employer"].last()


def balanced_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Only employers that reported in every year, so changes over time are not caused by
    different employers joining or leaving the data."""
    n_years = df["year"].nunique()
    years = df.groupby("employer_id")["year"].nunique()
    return df[df["employer_id"].isin(years[years == n_years].index)]


def trend(df: pd.DataFrame) -> pd.DataFrame:
    """Median of employers' median hourly pay gaps, by year: all reporters and the balanced panel."""
    panel = balanced_panel(df)
    out = pd.DataFrame({
        "employers_reporting": df.groupby("year").size(),
        "median_gap_all": df.groupby("year")["median_gap"].median(),
        "median_gap_same_employers": panel.groupby("year")["median_gap"].median(),
        "pct_paying_men_more": df.groupby("year")["median_gap"].apply(lambda s: 100 * (s > 0).mean()),
        "pct_submitted_late": df.groupby("year")["late"].mean() * 100,
    })
    out.attrs["panel_size"] = panel["employer_id"].nunique()
    return out.reset_index()


def employer_change(df: pd.DataFrame, start: int, end: int) -> pd.Series:
    """Change in each balanced-panel employer's median gap between two years (negative = narrowed)."""
    wide = balanced_panel(df).pivot_table(index="employer_id", columns="year", values="median_gap")
    return (wide[end] - wide[start]).rename("change_pts")


def by_sector(df: pd.DataFrame, year: int = LATEST) -> pd.DataFrame:
    y = df[df["year"] == year]
    g = y.groupby("sector")
    out = pd.DataFrame({
        "employers": g.size(),
        "median_gap": g["median_gap"].median(),
        "median_bonus_gap": g["median_bonus_gap"].median(),
        "women_in_top_quarter_pct": g["female_q4"].mean(),
        "women_in_bottom_quarter_pct": g["female_q1"].mean(),
        "women_overall_pct": g["female_share"].mean(),
    })
    out = out[(out["employers"] >= MIN_SECTOR_EMPLOYERS) & (out.index != "Not stated")]
    return out.sort_values("median_gap", ascending=False).reset_index()


def by_size(df: pd.DataFrame, year: int = LATEST) -> pd.DataFrame:
    y = df[(df["year"] == year) & (df["size_band"] != "Not Provided")]
    g = y.groupby("size_band", observed=True)
    return pd.DataFrame({"employers": g.size(), "median_gap": g["median_gap"].median()}).reset_index()


def quartile_shares(df: pd.DataFrame, year: int = LATEST) -> pd.Series:
    """Average share of women in each pay quarter (lowest-paid quarter of staff to highest)."""
    y = df[df["year"] == year]
    return y[["female_q1", "female_q2", "female_q3", "female_q4"]].mean().set_axis(
        ["Lowest paid", "Lower middle", "Upper middle", "Highest paid"])


def what_explains_the_gap(df: pd.DataFrame, year: int = LATEST) -> dict:
    """Compare two candidate explanations of an employer's gap: how many women it employs
    overall, versus how much less likely women are to be in its top pay quarter."""
    y = df[df["year"] == year].dropna(subset=["median_gap", "female_share", "top_vs_bottom_gap"])
    r_share = y["median_gap"].corr(y["female_share"])
    r_top = y["median_gap"].corr(y["top_vs_bottom_gap"])
    slope, intercept = np.polyfit(y["top_vs_bottom_gap"], y["median_gap"], 1)
    return {
        "employers": len(y),
        "corr_with_women_overall": r_share,
        "corr_with_top_vs_bottom": r_top,
        "r2_top_vs_bottom": r_top ** 2,
        "gap_pts_per_10pt_top_vs_bottom": 10 * slope,
        "intercept": intercept,
    }


def binned_relationship(df: pd.DataFrame, year: int = LATEST, width: int = 10) -> pd.DataFrame:
    """Median gap for employers grouped by how under-represented women are at the top."""
    y = df[df["year"] == year].dropna(subset=["top_vs_bottom_gap", "median_gap"])
    edges = np.arange(-40, 61, width)
    y = y[y["top_vs_bottom_gap"].between(edges[0], edges[-1], inclusive="left")]
    bins = pd.cut(y["top_vs_bottom_gap"], edges, right=False)
    g = y.groupby(bins, observed=True)["median_gap"]
    out = pd.DataFrame({"employers": g.size(), "median_gap": g.median()}).reset_index()
    out["bin_mid"] = [b.left + width / 2 for b in out["top_vs_bottom_gap"]]
    return out[out["employers"] >= 30]


def bonus_summary(df: pd.DataFrame, year: int = LATEST) -> dict:
    y = df[df["year"] == year]
    payers = y[(y["male_bonus_pct"] > 0) | (y["female_bonus_pct"] > 0)]
    return {
        "employers_paying_bonuses_pct": 100 * len(payers) / len(y),
        "median_bonus_gap_among_payers": payers["median_bonus_gap"].median(),
        "median_mean_bonus_gap_among_payers": payers["mean_bonus_gap"].median(),
    }
