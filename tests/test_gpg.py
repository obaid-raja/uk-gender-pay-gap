import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from gpg import analysis as A
from gpg import data


def test_sector_mapping():
    assert data.sector_of("1470") == "Agriculture, forestry & fishing"  # 01470, leading zero lost
    assert data.sector_of("64209") == "Finance & insurance"
    assert data.sector_of("85310") == "Education"
    assert data.sector_of("1") == "Public sector body"
    assert data.sector_of(None) == "Not stated"


def test_first_sic_takes_first_code():
    s = pd.Series(["85200,\n85310", None, "", "1"])
    assert data.first_sic(s).tolist() == ["85200", None, None, "1"]


def _raw(rows):
    cols = list(data.RENAME) + ["year", "ResponsiblePerson"]
    base = {c: 0.0 for c in cols}
    base.update(EmployerName="X", PostCode="L1", CompanyNumber="1", SicCodes=None,
                EmployerSize="250 to 499", SubmittedAfterTheDeadline=False, DateSubmitted="",
                ResponsiblePerson="A Person (a@b.com)")
    return pd.DataFrame([{**base, **r} for r in rows])


def test_tidy_drops_personal_data_and_fills_sic_within_employer():
    raw = _raw([
        dict(EmployerId=1, year=2017, SicCodes="64209"),
        dict(EmployerId=1, year=2018, SicCodes=None),
        dict(EmployerId=2, year=2017, SicCodes=None),
    ])
    df = data.tidy(raw.drop(columns="ResponsiblePerson"))
    assert "ResponsiblePerson" not in df.columns and "responsible_person" not in df.columns
    assert df.loc[df.employer_id == 1, "sector"].tolist() == ["Finance & insurance"] * 2
    assert df.loc[df.employer_id == 2, "sector"].item() == "Not stated"


def test_load_raw_never_keeps_personal_columns():
    assert "ResponsiblePerson" in data.DROP
    assert "ResponsiblePerson" not in data.RENAME


def test_balanced_panel_keeps_only_every_year_reporters():
    df = pd.DataFrame({"employer_id": [1, 1, 2], "year": [2017, 2018, 2017], "median_gap": [10, 8, 5]})
    assert A.balanced_panel(df)["employer_id"].unique().tolist() == [1]
    assert A.employer_change(df, 2017, 2018).loc[1] == pytest.approx(-2)


def test_processed_file_has_no_personal_columns():
    if not data.PROCESSED.exists():
        pytest.skip("processed data not built")
    cols = pd.read_csv(data.PROCESSED, nrows=1).columns
    assert not any("responsible" in c.lower() or "address" in c.lower() for c in cols)


def test_app_runs():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception
    assert len(at.tabs) == 3
