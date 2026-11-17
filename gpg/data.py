"""Load the GOV.UK gender pay gap reports (one CSV per snapshot year) into one tidy table.

Source: https://gender-pay-gap.service.gov.uk/viewing/download (Open Government Licence v3.0).
Employers with 250+ staff must report every year. "Year" here is the snapshot year: pay on
31 March (public sector) or 5 April (private and voluntary sector) of that year.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed" / "gpg_reports.csv.gz"
YEARS = range(2017, 2026)
DOWNLOAD_URL = "https://gender-pay-gap.service.gov.uk/viewing/download-data/{year}"

# Dropped on load: ResponsiblePerson holds a named individual (often with an email address),
# and address / links are not needed for the analysis.
DROP = ["ResponsiblePerson", "Address", "CompanyLinkToGPGInfo", "CurrentName", "DueDate"]

RENAME = {
    "EmployerName": "employer", "EmployerId": "employer_id", "PostCode": "postcode",
    "CompanyNumber": "company_number", "SicCodes": "sic_codes",
    "DiffMeanHourlyPercent": "mean_gap", "DiffMedianHourlyPercent": "median_gap",
    "DiffMeanBonusPercent": "mean_bonus_gap", "DiffMedianBonusPercent": "median_bonus_gap",
    "MaleBonusPercent": "male_bonus_pct", "FemaleBonusPercent": "female_bonus_pct",
    "FemaleLowerQuartile": "female_q1", "FemaleLowerMiddleQuartile": "female_q2",
    "FemaleUpperMiddleQuartile": "female_q3", "FemaleTopQuartile": "female_q4",
    "EmployerSize": "size_band", "SubmittedAfterTheDeadline": "late",
    "DateSubmitted": "date_submitted",
}

SIZE_ORDER = ["Less than 250", "250 to 499", "500 to 999", "1000 to 4999",
              "5000 to 19,999", "20,000 or more", "Not Provided"]

# UK SIC 2007: two-digit division -> section.
SECTIONS = [
    (1, 3, "Agriculture, forestry & fishing"), (5, 9, "Mining & quarrying"),
    (10, 33, "Manufacturing"), (35, 35, "Energy supply"), (36, 39, "Water & waste"),
    (41, 43, "Construction"), (45, 47, "Wholesale & retail"), (49, 53, "Transport & storage"),
    (55, 56, "Hospitality"), (58, 63, "Information & communication"),
    (64, 66, "Finance & insurance"), (68, 68, "Real estate"),
    (69, 75, "Professional, scientific & technical"), (77, 82, "Administrative & support"),
    (84, 84, "Public administration & defence"), (85, 85, "Education"),
    (86, 88, "Health & social work"), (90, 93, "Arts & recreation"),
    (94, 96, "Other services"), (97, 98, "Households as employers"),
    (99, 99, "Extraterritorial bodies"),
]


def download(years=YEARS, force: bool = False) -> None:
    import urllib.request
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for y in years:
        path = RAW_DIR / f"gpg_{y}.csv"
        if force or not path.exists():
            urllib.request.urlretrieve(DOWNLOAD_URL.format(year=y), path)


def first_sic(codes: pd.Series) -> pd.Series:
    """First listed SIC code as a 5-digit string. The download drops leading zeros
    ('1470' is 01470); the code '1' is used for public bodies that give no SIC code."""
    first = codes.fillna("").astype(str).str.split(",").str[0].str.strip()
    return first.where(first != "", None)


def sector_of(code) -> str:
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return "Not stated"
    if code == "1":
        return "Public sector body"
    division = int(code.zfill(5)[:2])
    for lo, hi, name in SECTIONS:
        if lo <= division <= hi:
            return name
    return "Not stated"


def load_raw(years=YEARS) -> pd.DataFrame:
    frames = []
    for y in years:
        d = pd.read_csv(RAW_DIR / f"gpg_{y}.csv", dtype={"CompanyNumber": str, "SicCodes": str})
        frames.append(d.drop(columns=[c for c in DROP if c in d.columns]).assign(year=y))
    return pd.concat(frames, ignore_index=True)


def tidy(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=RENAME)
    df = df[["year"] + list(RENAME.values())]
    # Male quartile shares are 100 - female shares, so they are not kept.
    df["sic"] = first_sic(df["sic_codes"])
    # Employers sometimes leave the SIC code blank in one year but give it in another:
    # fill a missing code with the same employer's code from its nearest other year.
    df = df.sort_values(["employer_id", "year"])
    df["sic"] = df.groupby("employer_id")["sic"].transform(lambda s: s.ffill().bfill())
    df["sector"] = [sector_of(c) for c in df["sic"]]
    df["female_share"] = df[["female_q1", "female_q2", "female_q3", "female_q4"]].mean(axis=1)
    # How far women are under-represented in the top pay quarter compared with the bottom.
    df["top_vs_bottom_gap"] = df["female_q1"] - df["female_q4"]
    df["late"] = df["late"].astype(bool)
    df["size_band"] = pd.Categorical(df["size_band"], SIZE_ORDER, ordered=True)
    return df.drop(columns="sic_codes").reset_index(drop=True)


def build() -> pd.DataFrame:
    df = tidy(load_raw())
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False, compression="gzip")
    return df


def load() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED, dtype={"company_number": str, "sic": str})
    df["size_band"] = pd.Categorical(df["size_band"], SIZE_ORDER, ordered=True)
    return df
