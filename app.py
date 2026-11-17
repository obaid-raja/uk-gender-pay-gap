"""UK Gender Pay Gap Explorer: look up any employer and compare it with its sector and the UK.

    streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gpg import analysis as A
from gpg import data

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#898781"

st.set_page_config(page_title="UK Gender Pay Gap Explorer", page_icon="📊", layout="wide")


@st.cache_data
def load():
    df = data.load()
    names = A.latest_names(df)
    df["employer_latest"] = df["employer_id"].map(names)
    return df


df = load()
years = sorted(df["year"].unique())
national = df.groupby("year")["median_gap"].median()

st.title("UK Gender Pay Gap Explorer")
st.caption(f"{len(df):,} official reports from {df['employer_id'].nunique():,} UK employers, "
           f"{years[0]} to {years[-1]}. Source: GOV.UK gender pay gap service (OGL v3.0). "
           "A positive gap means men earn more per hour than women at that employer.")

tab_emp, tab_sector, tab_about = st.tabs(["Look up an employer", "Compare sectors", "How to read this"])

with tab_emp:
    options = df.drop_duplicates("employer_id").sort_values("employer_latest")
    labels = dict(zip(options["employer_id"], options["employer_latest"]))
    default = next((i for i, n in labels.items() if "TESCO STORES" in n.upper()), options["employer_id"].iat[0])
    emp_id = st.selectbox("Employer (start typing to search)", list(labels), format_func=labels.get,
                          index=list(labels).index(default))
    e = df[df["employer_id"] == emp_id].sort_values("year")
    last = e.iloc[-1]
    sector = last["sector"]
    sector_med = df[df["sector"] == sector].groupby("year")["median_gap"].median()

    c = st.columns(4)
    c[0].metric(f"Median hourly gap, {last['year']}", f"{last['median_gap']:.1f}%",
                None if len(e) < 2 else f"{last['median_gap'] - e['median_gap'].iat[0]:+.1f} pts since {e['year'].iat[0]}",
                delta_color="inverse")
    c[1].metric(f"{sector} median", f"{sector_med.get(last['year'], float('nan')):.1f}%")
    c[2].metric("UK median (all employers)", f"{national[last['year']]:.1f}%")
    c[3].metric("Women in top pay quarter", f"{last['female_q4']:.0f}%",
                f"{last['female_q4'] - last['female_q1']:+.0f} pts vs lowest quarter", delta_color="off")

    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure()
        fig.add_scatter(x=e["year"], y=e["median_gap"], name=labels[emp_id][:40], mode="lines+markers",
                        line=dict(color=BLUE, width=2))
        fig.add_scatter(x=sector_med.index, y=sector_med.values, name=f"{sector} median",
                        mode="lines", line=dict(color=ORANGE, width=2))
        fig.add_scatter(x=national.index, y=national.values, name="UK median", mode="lines",
                        line=dict(color=GREY, width=2, dash="dot"))
        fig.add_hline(y=0, line_color="#c3c2b7", line_width=1)
        fig.update_layout(title="Median hourly pay gap over time", yaxis_ticksuffix="%",
                          hovermode="x unified", height=380, margin=dict(l=10, r=10, t=50, b=10),
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
    with right:
        q = [last["female_q1"], last["female_q2"], last["female_q3"], last["female_q4"]]
        fig = go.Figure(go.Bar(x=["Lowest paid", "Lower middle", "Upper middle", "Highest paid"], y=q,
                               marker_color=BLUE, text=[f"{v:.0f}%" for v in q], textposition="outside"))
        fig.add_hline(y=50, line_dash="dot", line_color=GREY)
        fig.update_layout(title=f"Women's share of each pay quarter, {last['year']}",
                          yaxis=dict(range=[0, 110], ticksuffix="%"), height=380,
                          margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, width="stretch")

    show = e[["year", "median_gap", "mean_gap", "median_bonus_gap", "male_bonus_pct", "female_bonus_pct",
              "female_q1", "female_q4", "size_band", "late"]].rename(columns={
        "median_gap": "Median gap %", "mean_gap": "Mean gap %", "median_bonus_gap": "Median bonus gap %",
        "male_bonus_pct": "Men getting bonus %", "female_bonus_pct": "Women getting bonus %",
        "female_q1": "Women in lowest quarter %", "female_q4": "Women in top quarter %",
        "size_band": "Employees", "late": "Submitted late"})
    st.dataframe(show.set_index("year"), width="stretch")

with tab_sector:
    year = st.select_slider("Snapshot year", years, value=years[-1])
    s = A.by_sector(df, year)
    fig = go.Figure(go.Bar(y=s["sector"][::-1], x=s["median_gap"][::-1], orientation="h",
                           marker_color=BLUE, text=[f"{v:.1f}%" for v in s["median_gap"][::-1]],
                           textposition="outside",
                           customdata=s[["employers", "women_in_top_quarter_pct"]][::-1].values,
                           hovertemplate="%{y}<br>Median gap %{x:.1f}%<br>%{customdata[0]} employers"
                                         "<br>Women in top quarter %{customdata[1]:.0f}%<extra></extra>"))
    fig.update_layout(title=f"Median hourly pay gap by sector, {year}", xaxis_ticksuffix="%",
                      height=620, margin=dict(l=10, r=40, t=50, b=10))
    st.plotly_chart(fig, width="stretch")

    pick = st.selectbox("Employers in sector", s["sector"])
    sub = df[(df["year"] == year) & (df["sector"] == pick)]
    st.dataframe(sub[["employer_latest", "median_gap", "mean_gap", "female_q1", "female_q4", "size_band"]]
                 .rename(columns={"employer_latest": "Employer", "median_gap": "Median gap %",
                                  "mean_gap": "Mean gap %", "female_q1": "Women in lowest quarter %",
                                  "female_q4": "Women in top quarter %", "size_band": "Employees"})
                 .sort_values("Median gap %", ascending=False), hide_index=True, width="stretch")

with tab_about:
    st.markdown("""
**The pay gap is not the same as unequal pay.** Unequal pay (paying a woman less for the same job) has been
illegal since 1970. The gender pay gap compares the *average* hourly pay of all women and all men at an
employer, so it mostly reflects **who does which jobs**: if men hold most senior roles, the gap is large
even when everyone in the same job is paid the same.

- **Median gap:** the middle-paid woman versus the middle-paid man. Less affected by a few very high earners.
- **Pay quarters:** each employer ranks all staff by hourly pay and splits them into four equal groups.
- **Year:** the snapshot date (5 April for private and voluntary employers, 31 March for the public sector).
  Reports are due a year later.
- **2019:** enforcement was suspended because of COVID-19, so only about 7,000 employers reported.
- **Sector:** taken from the first industry (SIC) code the employer lists. "Public sector body" means a public
  employer that did not give a code, such as councils, NHS trusts and universities.
""")
