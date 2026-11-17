"""Static charts for the README. The interactive version is the Streamlit app."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2, "axes.titlecolor": INK, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": INK_2,
    "axes.spines.top": False, "axes.spines.right": False,
    "savefig.dpi": 160, "savefig.bbox": "tight",
})
PCT = mtick.PercentFormatter(decimals=0)


def trend(t, path):
    fig, ax = plt.subplots(figsize=(8.5, 4))
    n = t.attrs.get("panel_size", "")
    ax.plot(t["year"], t["median_gap_same_employers"], color=BLUE, linewidth=2, marker="o",
            markersize=5, label=f"Same {n:,} employers every year")
    ax.plot(t["year"], t["median_gap_all"], color=ORANGE, linewidth=2, marker="o", markersize=5,
            label="All employers reporting that year")
    for col, dy in (("median_gap_same_employers", 8), ("median_gap_all", -14)):
        for i in (0, len(t) - 1):
            ax.annotate(f"{t[col].iat[i]:.1f}%", (t["year"].iat[i], t[col].iat[i]),
                        xytext=(0, dy), textcoords="offset points", ha="center", fontsize=8.5,
                        color=INK_2)
    ax.set_ylim(0, 14)
    r19 = t[t["year"] == 2019]
    if len(r19):
        ax.annotate(f"2019: only {r19['employers_reporting'].iat[0]:,} reports\n"
                    "(enforcement suspended for COVID-19)",
                    (2019, r19["median_gap_all"].iat[0]), xytext=(2019, 5), ha="center",
                    fontsize=8.5, color=INK_2,
                    arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xticks(t["year"])
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, colors=MUTED)
    ax.legend(frameon=False, loc="lower left", labelcolor=INK_2)
    ax.set_title("Median hourly pay gap (men over women), by snapshot year")
    fig.savefig(path)
    plt.close(fig)


def sectors(s, path):
    s = s.iloc[::-1]
    y = np.arange(len(s))
    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.barh(y, s["median_gap"], 0.62, color=BLUE)
    for yi, v, n in zip(y, s["median_gap"], s["employers"]):
        ax.text(v + 0.3, yi, f"{v:.1f}%", va="center", fontsize=8.5, color=INK_2)
    ax.set_yticks(y, [f"{a}  ({n:,})" for a, n in zip(s["sector"], s["employers"])])
    ax.xaxis.set_major_formatter(PCT)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Median hourly pay gap by sector, 2025 (number of employers)")
    fig.savefig(path)
    plt.close(fig)


def quartiles(q, path):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = np.arange(len(q))
    ax.bar(x, q.values, 0.6, color=BLUE)
    for xi, v in zip(x, q.values):
        ax.text(xi, v + 1, f"{v:.0f}%", ha="center", fontsize=9, color=INK_2)
    ax.axhline(50, color=INK_2, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(len(q) - 0.5, 51, "50%", fontsize=8.5, color=INK_2, ha="right")
    ax.set_xticks(x, q.index)
    ax.set_ylim(0, 65)
    ax.yaxis.set_major_formatter(PCT)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, colors=MUTED)
    ax.set_xlabel("Each employer's staff split into four equal groups by hourly pay")
    ax.set_title("Women's share of each pay quarter, average employer, 2025")
    fig.savefig(path)
    plt.close(fig)


def relationship(b, path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(b["bin_mid"], b["median_gap"], color=BLUE, linewidth=2, marker="o", markersize=6)
    for x, v, n in zip(b["bin_mid"], b["median_gap"], b["employers"]):
        ax.annotate(f"{int(round(v))}%", (x, v), xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=8.5, color=INK_2)
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.axvline(0, color=AXIS, linewidth=1)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:+.0f} pts"))
    ax.yaxis.set_major_formatter(PCT)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, colors=MUTED)
    ax.set_xlabel("Women's share of the lowest-paid quarter minus their share of the highest-paid quarter")
    ax.set_title("The fewer women at the top relative to the bottom, the bigger the gap (2025)")
    fig.savefig(path)
    plt.close(fig)
