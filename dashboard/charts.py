"""Plotly figure builders for the narrative sections.

Every builder takes a preset list and returns a static-but-hoverable Plotly
figure. Plotly gives tooltips and legend-click show/hide for free — that is the
only interactivity the narrative sections need.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import prep

SOC_COLOR = "#555555"
POC_COLOR = "#0E7490"
OVER_COLOR = "#B35806"
UNDER_COLOR = "#2E86C1"
PALETTE = ["#0E7490", "#B35806", "#2E86C1", "#6A9F58", "#A6449B",
           "#C2871C", "#D6604D", "#4F6D7A"]

_LAYOUT = dict(template="simple_white", margin=dict(l=55, r=15, t=40, b=45),
               font=dict(size=12), legend=dict(title_text=""))


def _err(df, med="median", p25="p25", p75="p75"):
    """Asymmetric IQR error-bar spec from a median/p25/p75 column trio."""
    return dict(type="data", visible=True, thickness=1.2, width=3, color="#333",
                array=(df[p75] - df[med]).to_numpy(),
                arrayminus=(df[med] - df[p25]).to_numpy())


def bar_grid(long, presets, metric, y_label):
    """2x2 endpoint-bar grid (one panel per disease), IQR error bars, indep. y."""
    fig = make_subplots(rows=2, cols=2, subplot_titles=[lbl for _, lbl in prep.DISEASES],
                        vertical_spacing=0.14, horizontal_spacing=0.10)
    for i, (d, _lbl) in enumerate(prep.DISEASES):
        r, c = i // 2 + 1, i % 2 + 1
        df = prep.preset_bar(long, presets, d, metric)
        colors = [SOC_COLOR if s else POC_COLOR for s in df["is_soc"]]
        fig.add_bar(x=df["label"], y=df["median"], marker_color=colors,
                    error_y=_err(df), showlegend=False, row=r, col=c,
                    hovertemplate="%{x}<br>%{y:.3f}<extra></extra>")
    fig.update_layout(height=560, **_LAYOUT)
    fig.update_yaxes(title_text=y_label, col=1)
    fig.update_xaxes(tickangle=-25, tickfont=dict(size=10))
    return fig


def ts_grid(ts, presets, metric, y_label):
    """2x2 timeseries grid (one panel per disease); palette per preset, shared legend."""
    fig = make_subplots(rows=2, cols=2, subplot_titles=[lbl for _, lbl in prep.DISEASES],
                        vertical_spacing=0.14, horizontal_spacing=0.10)
    # Color by preset position (as the React version did): SOC gray, then PALETTE[i].
    color_map = {p["label"]: (SOC_COLOR if p["key"] == "soc" else PALETTE[i % len(PALETTE)])
                 for i, p in enumerate(presets)}
    for i, (d, _lbl) in enumerate(prep.DISEASES):
        r, c = i // 2 + 1, i % 2 + 1
        df = prep.preset_ts(ts, presets, d, metric)
        for label, sub in df.groupby("label", sort=False):
            is_soc = bool(sub["is_soc"].iloc[0])
            color = color_map.get(label, PALETTE[0])
            fig.add_scatter(x=sub["year"], y=sub["value"], name=label, legendgroup=label,
                            showlegend=(i == 0), mode="lines",
                            line=dict(color=color, width=2.6 if is_soc else 1.8, shape="spline"),
                            row=r, col=c, hovertemplate=f"{label}<br>%{{x}}: %{{y:.3f}}<extra></extra>")
    fig.update_layout(height=560, **_LAYOUT)
    fig.update_yaxes(title_text=y_label, col=1)
    return fig


def notif_fig(long, presets):
    """Grouped over-/under-notification bars across presets, with IQR error bars."""
    df = prep.preset_notification(long, presets)
    fig = go.Figure()
    fig.add_bar(name="Over-notification", x=df["label"], y=df["over_median"],
                marker_color=OVER_COLOR, error_y=_err(df, "over_median", "over_p25", "over_p75"),
                hovertemplate="%{x}<br>over %{y:.3f}<extra></extra>")
    fig.add_bar(name="Under-notification", x=df["label"], y=df["under_median"],
                marker_color=UNDER_COLOR, error_y=_err(df, "under_median", "under_p25", "under_p75"),
                hovertemplate="%{x}<br>under %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", height=400, yaxis_title="Rate", **_LAYOUT)
    fig.update_layout(  # title inside the figure, matching the subplot-title style
        title=dict(text="Partner notification", x=0.5, xanchor="center",
                   font=dict(size=16, color="#2a3f5f")),
        margin=dict(l=55, r=15, t=55, b=45))
    fig.update_xaxes(tickangle=-25, tickfont=dict(size=10))
    return fig
