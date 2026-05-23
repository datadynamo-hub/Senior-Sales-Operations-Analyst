import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Sorenson RevOps Center",
    page_icon=":bar_chart:",
    layout="wide"
)

# ── Data loader ───────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    pipeline = pd.read_csv("data/pipeline.csv", parse_dates=["close_date"])
    revenue = pd.read_csv("data/revenue.csv")
    reps = pd.read_csv("data/reps.csv")
    return pipeline, revenue, reps

pipeline_df, revenue_df, reps_df = load_data()

# ── Shared constants ──────────────────────────────────────────────────────────

_MOTION_COLORS = {
    "New": "#2563EB",
    "Expansion": "#16A34A",
    "Renewal": "#D97706",
    "Churn": "#DC2626",
}
_STAGE_ORDER = ["Prospect", "Qualified", "Demo", "Proposal", "Negotiation"]
_STAGE_BENCHMARKS = {
    "Prospect": 7,
    "Qualified": 14,
    "Demo": 14,
    "Proposal": 21,
    "Negotiation": 28,
}
_DEMO_TODAY = pd.Timestamp("2026-05-22")
_SPRINT_DAYS = 60

_ALL_SERVICE_LINES = sorted(revenue_df["service_line"].unique().tolist())
_ALL_MOTIONS_REV = sorted(m for m in revenue_df["motion"].unique() if m != "Churn")
_ALL_MONTHS = sorted(revenue_df["month"].unique().tolist())
_ALL_TERRITORIES = sorted(reps_df["territory"].unique().tolist())

# ── Risk scoring ──────────────────────────────────────────────────────────────

@st.cache_data
def _add_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def _score(row):
        bench = _STAGE_BENCHMARKS.get(row["stage"], 14)
        days_score = min(40, int((row["days_in_stage"] / bench) * 20))
        flag_score = 35 if row["risk_flag"] else 0
        arr_score = 15 if row["ARR"] >= 75_000 else 0
        return min(100, days_score + flag_score + arr_score)

    def _reason(row):
        bench = _STAGE_BENCHMARKS.get(row["stage"], 14)
        parts = []
        if row["days_in_stage"] >= bench * 2:
            parts.append(f"{row['days_in_stage']}d in {row['stage']} (2x the {bench}d benchmark)")
        elif row["days_in_stage"] >= bench:
            parts.append(f"approaching stage limit ({bench}d benchmark)")
        if row["risk_flag"]:
            parts.append("flagged: discount or low engagement")
        if row["ARR"] >= 75_000:
            parts.append("high-value deal")
        return "; ".join(parts) if parts else "within norms"

    def _level(s: int) -> str:
        if s < 25:
            return "Low"
        if s < 50:
            return "Medium"
        if s < 75:
            return "High"
        return "Critical"

    df["risk_score"] = df.apply(_score, axis=1)
    df["risk_level"] = df["risk_score"].apply(_level)
    df["risk_reason"] = df.apply(_reason, axis=1)
    return df

# ── Comp plan simulator ───────────────────────────────────────────────────────

def _sim_bonus(
    attainment_pct: float,
    variable_target: float,
    floor: float,
    full_pay: float,
    accel: float,
) -> float:
    """
    Current plan structure (verified against data):
      < floor       → $0
      floor–full_pay → 50% of variable target (flat)
      full_pay–100% → 100% of variable target
      100%+         → variable_target × accel  (flat above-quota multiplier)
    """
    if attainment_pct < floor:
        return 0.0
    elif attainment_pct < full_pay:
        return variable_target * 0.5
    elif attainment_pct < 1.0:
        return float(variable_target)
    else:
        return variable_target * accel

# ── Session state defaults ────────────────────────────────────────────────────

_DEFAULTS: dict = {
    "pipeline_view": "All deals",
    "rev_service_lines": _ALL_SERVICE_LINES,
    "rev_motions": _ALL_MOTIONS_REV,
    "rev_month_range": (_ALL_MONTHS[0], _ALL_MONTHS[-1]),
    "rep_territories": _ALL_TERRITORIES,
    "quota_adj": 0,
    "floor_pct": 50,
    "full_pay_pct": 80,
    "accel_mult": 1.25,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Sorenson RevOps Center")
st.markdown("Pipeline, forecast, and revenue tracking built around how Sorenson actually sells.")
st.caption(
    "Built by [Jon Khan](https://www.linkedin.com/in/jonathan-k-184393120/) "
    "· [LinkedIn](https://www.linkedin.com/in/jonathan-k-184393120/) "
    "· Forked from [munas-git](https://github.com/munas-git/AI-powered-sales-dashboard)"
)
st.info("All revenue and pipeline data displayed is simulated in real time to demonstrate system capabilities.")
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Executive Summary",
        "Pipeline and Forecast",
        "Multi-Motion Revenue",
        "Rep Productivity and Compensation",
    ],
    on_change="rerun",
)

# ── Tab 1: Executive Summary ──────────────────────────────────────────────────

with tab1:
    open_deals = pipeline_df[~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])]

    total_pipeline = open_deals["ARR"].sum()
    total_quota = reps_df["quota"].sum()
    coverage = total_pipeline / total_quota

    latest_months = sorted(revenue_df["month"].unique())[-3:]
    qtd = revenue_df[revenue_df["month"].isin(latest_months)]
    renewal_mrr = qtd[qtd["motion"] == "Renewal"]["MRR"].sum()
    expansion_mrr = qtd[qtd["motion"] == "Expansion"]["MRR"].sum()
    churn_mrr = qtd[qtd["motion"] == "Churn"]["MRR"].sum()
    ndr = (renewal_mrr + expansion_mrr + churn_mrr) / renewal_mrr if renewal_mrr else 0
    expansion_rate = expansion_mrr / renewal_mrr if renewal_mrr else 0
    contraction_rate = churn_mrr / renewal_mrr if renewal_mrr else 0

    reps_above_80 = int((reps_df["attainment_pct"] >= 0.80).sum())
    total_reps = len(reps_df)

    sla_rate = revenue_df["sla_met"].mean()
    util_rate = revenue_df["utilized_hours"].sum() / revenue_df["contracted_hours"].sum()

    velocity_new = open_deals[open_deals["motion"] == "New"]["days_in_stage"].mean()
    velocity_renewal = open_deals[open_deals["motion"] == "Renewal"]["days_in_stage"].mean()

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(
            label="Pipeline Coverage Ratio",
            value=f"{coverage:.1f}x",
            delta=f"{coverage - 3.0:+.1f}x vs 3.0x target",
            border=True,
        )
    with c2:
        st.metric(
            label="Net Dollar Retention",
            value=f"{ndr:.0%}",
            delta=f"Expansion {expansion_rate:+.0%}, Contraction {contraction_rate:.0%}",
            delta_color="off",
            border=True,
        )
    with c3:
        st.metric(
            label="Quota Attainment",
            value=f"{reps_above_80} of {total_reps} reps",
            delta=f"{reps_above_80 / total_reps:.0%} at or above 80%",
            delta_color="off",
            border=True,
        )
    with c4:
        st.metric(
            label="Service Level Agreement Compliance",
            value=f"{sla_rate:.1%}",
            delta=f"{sla_rate - 0.95:+.1%} vs 95% target",
            border=True,
        )
    with c5:
        st.metric(
            label="Interpreting Hours Utilization",
            value=f"{util_rate:.0%}",
            delta="of contracted hours used",
            delta_color="off",
            border=True,
        )

    # ── Deal velocity ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Average deal velocity")
    v1, v2 = st.columns(2)
    with v1:
        st.metric(
            label="New Business",
            value=f"{velocity_new:.0f} days",
            delta="average days in current stage",
            delta_color="off",
            border=True,
        )
    with v2:
        st.metric(
            label="Renewal",
            value=f"{velocity_renewal:.0f} days",
            delta="average days in current stage",
            delta_color="off",
            border=True,
        )

    # ── Sprint to close ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Closing in the next {_SPRINT_DAYS} days")

    sprint = open_deals[
        (open_deals["close_date"] >= _DEMO_TODAY) &
        (open_deals["close_date"] <= _DEMO_TODAY + pd.Timedelta(days=_SPRINT_DAYS))
    ].sort_values("close_date")

    sp1, sp2, sp3 = st.columns(3)
    with sp1:
        st.metric("Deals in window", len(sprint), border=True)
    with sp2:
        st.metric("Pipeline at stake", f"${sprint['ARR'].sum():,.0f}", border=True)
    with sp3:
        st.metric("Risk-flagged in window", int(sprint["risk_flag"].sum()), border=True)

    if len(sprint) > 0:
        st.dataframe(
            sprint[["rep_name", "motion", "stage", "ARR", "close_date", "risk_flag"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "rep_name": "Rep",
                "motion": "Motion",
                "stage": "Stage",
                "ARR": st.column_config.NumberColumn("Annual recurring revenue", format="$%.0f"),
                "close_date": st.column_config.DateColumn("Close date", format="MMM D, YYYY"),
                "risk_flag": st.column_config.CheckboxColumn("Risk flag"),
            },
        )
    else:
        st.info("No open deals closing within the next 60 days.")

# ── Tab 2: Pipeline and Forecast ──────────────────────────────────────────────

with tab2:
    open_t2 = pipeline_df[~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])].copy()
    open_t2_scored = _add_risk_scores(open_t2)

    view = st.session_state.get("pipeline_view", "All deals")
    filtered = open_t2_scored[open_t2_scored["risk_flag"]] if view == "Risk flagged only" else open_t2_scored

    # ── Pipeline funnel ───────────────────────────────────────────────────────
    st.subheader("Open pipeline by stage and motion")

    funnel_data = (
        filtered[filtered["stage"].isin(_STAGE_ORDER)]
        .groupby(["stage", "motion"])
        .size()
        .reset_index(name="deal_count")
    )
    funnel_data["stage"] = pd.Categorical(funnel_data["stage"], categories=_STAGE_ORDER, ordered=True)
    funnel_data = funnel_data.sort_values("stage")

    fig_funnel = px.bar(
        funnel_data,
        x="stage",
        y="deal_count",
        color="motion",
        barmode="group",
        labels={"stage": "Stage", "deal_count": "Number of deals", "motion": "Motion"},
        color_discrete_map=_MOTION_COLORS,
    )
    fig_funnel.update_layout(legend_title_text="Motion")
    st.plotly_chart(fig_funnel, use_container_width=True)

    # ── Quarterly forecast rollup ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Quarterly forecast rollup")

    _STAGE_TO_CAT = {
        "Negotiation": "Committed",
        "Proposal": "Best Case",
        "Demo": "Upside",
        "Qualified": "Upside",
        "Prospect": "Upside",
    }
    rollup = filtered.copy()
    rollup["category"] = rollup["stage"].map(_STAGE_TO_CAT)
    rollup = rollup.dropna(subset=["category"])
    rollup["quarter"] = rollup["close_date"].dt.to_period("Q").astype(str)

    quarterly = (
        rollup.groupby(["quarter", "category"])["ARR"]
        .sum()
        .reset_index()
        .pivot(index="quarter", columns="category", values="ARR")
        .fillna(0)
        .reset_index()
    )
    quarterly.columns.name = None
    for col in ["Committed", "Best Case", "Upside"]:
        if col not in quarterly.columns:
            quarterly[col] = 0.0
    quarterly = quarterly[["quarter", "Committed", "Best Case", "Upside"]].sort_values("quarter")
    quarterly["Total"] = quarterly["Committed"] + quarterly["Best Case"] + quarterly["Upside"]

    st.dataframe(
        quarterly,
        hide_index=True,
        use_container_width=True,
        column_config={
            "quarter": "Quarter",
            "Committed": st.column_config.NumberColumn("Committed", format="$%.0f"),
            "Best Case": st.column_config.NumberColumn("Best Case", format="$%.0f"),
            "Upside": st.column_config.NumberColumn("Upside", format="$%.0f"),
            "Total": st.column_config.NumberColumn("Total", format="$%.0f"),
        },
    )

    # ── Pipeline coverage gap ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Pipeline coverage vs quarterly quota target")

    cov_df = open_t2.copy()
    cov_df["quarter"] = cov_df["close_date"].dt.to_period("Q").astype(str)
    pipe_by_q = cov_df.groupby("quarter")["ARR"].sum().reset_index()
    quarterly_quota_target = reps_df["quota"].sum() / 4
    pipe_by_q["quota_target"] = quarterly_quota_target
    pipe_by_q["coverage_ratio"] = (pipe_by_q["ARR"] / quarterly_quota_target).round(2)

    fig_cov = go.Figure()
    fig_cov.add_bar(
        x=pipe_by_q["quarter"],
        y=pipe_by_q["ARR"],
        name="Pipeline annual recurring revenue",
        marker_color="#2563EB",
        text=pipe_by_q["coverage_ratio"].apply(lambda x: f"{x:.1f}x"),
        textposition="outside",
    )
    fig_cov.add_scatter(
        x=pipe_by_q["quarter"],
        y=pipe_by_q["quota_target"],
        name="Quarterly quota target",
        mode="lines+markers",
        line={"color": "#DC2626", "dash": "dash", "width": 2},
        marker={"size": 8},
    )
    fig_cov.update_layout(
        yaxis_title="Annual recurring revenue ($)",
        xaxis_title="Quarter",
        legend_title="",
        bargap=0.4,
    )
    st.plotly_chart(fig_cov, use_container_width=True)

    # ── Deal velocity ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Average days in stage by motion")

    velocity = (
        open_t2.groupby(["stage", "motion"])["days_in_stage"]
        .mean()
        .round(1)
        .reset_index()
    )
    velocity["stage"] = pd.Categorical(velocity["stage"], categories=_STAGE_ORDER, ordered=True)
    velocity = velocity[velocity["stage"].isin(_STAGE_ORDER)].sort_values("stage")

    fig_velocity = px.bar(
        velocity,
        x="stage",
        y="days_in_stage",
        color="motion",
        barmode="group",
        labels={"stage": "Stage", "days_in_stage": "Average days", "motion": "Motion"},
        color_discrete_map=_MOTION_COLORS,
    )
    fig_velocity.update_layout(legend_title_text="Motion")
    st.plotly_chart(fig_velocity, use_container_width=True)

    # ── Risk-scored deal list ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Deal risk assessment")

    deal_list = filtered[
        ["rep_name", "motion", "stage", "ARR", "close_date",
         "risk_score", "risk_level", "risk_reason"]
    ].copy().sort_values(["risk_score", "close_date"], ascending=[False, True])

    st.dataframe(
        deal_list,
        hide_index=True,
        use_container_width=True,
        column_config={
            "rep_name": "Rep",
            "motion": "Motion",
            "stage": "Stage",
            "ARR": st.column_config.NumberColumn("Annual recurring revenue", format="$%.0f"),
            "close_date": st.column_config.DateColumn("Close date", format="MMM D, YYYY"),
            "risk_score": st.column_config.ProgressColumn(
                "Risk score", min_value=0, max_value=100, format="%d"
            ),
            "risk_level": "Risk level",
            "risk_reason": "Risk reason",
        },
    )

# ── Tab 3: Multi-Motion Revenue ───────────────────────────────────────────────

with tab3:
    sel_sl = st.session_state.get("rev_service_lines", _ALL_SERVICE_LINES)
    sel_motions = st.session_state.get("rev_motions", _ALL_MOTIONS_REV)
    month_range = st.session_state.get("rev_month_range", (_ALL_MONTHS[0], _ALL_MONTHS[-1]))

    rev = revenue_df[
        (revenue_df["service_line"].isin(sel_sl)) &
        (revenue_df["month"] >= month_range[0]) &
        (revenue_df["month"] <= month_range[1])
    ].copy()

    # ── Monthly recurring revenue by motion ───────────────────────────────────
    st.subheader("Monthly contract value by motion")

    mrr_line = (
        rev[rev["motion"].isin(sel_motions)]
        .groupby(["month", "motion"])["MRR"]
        .sum()
        .reset_index()
    )
    fig_mrr = px.line(
        mrr_line,
        x="month",
        y="MRR",
        color="motion",
        markers=True,
        labels={"month": "Month", "MRR": "Monthly recurring revenue ($)", "motion": "Motion"},
        color_discrete_map=_MOTION_COLORS,
    )
    fig_mrr.update_layout(legend_title_text="Motion")
    st.plotly_chart(fig_mrr, use_container_width=True)

    # ── NDR and GDR ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Retention metrics (trailing 3 months)")

    _latest_3 = sorted(revenue_df["month"].unique())[-3:]
    _wf = revenue_df[revenue_df["month"].isin(_latest_3)]
    _renewal = _wf[_wf["motion"] == "Renewal"]["MRR"].sum()
    _expansion = _wf[_wf["motion"] == "Expansion"]["MRR"].sum()
    _churn = _wf[_wf["motion"] == "Churn"]["MRR"].sum()
    _ending = _renewal + _expansion + _churn
    _ndr = _ending / _renewal if _renewal else 0
    _gdr = (_renewal + _churn) / _renewal if _renewal else 0

    r1, r2 = st.columns(2)
    with r1:
        st.metric(
            label="Net Dollar Retention",
            value=f"{_ndr:.1%}",
            delta="Renewal + Expansion + Churn / Beginning Renewal",
            delta_color="off",
            border=True,
        )
    with r2:
        st.metric(
            label="Gross Dollar Retention",
            value=f"{_gdr:.1%}",
            delta="Excludes expansion — measures pure renewal retention",
            delta_color="off",
            border=True,
        )

    st.markdown("")

    fig_waterfall = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["Beginning renewal", "Expansion", "Contraction and churn", "Ending"],
        y=[_renewal, _expansion, _churn, 0],
        text=[
            f"${_renewal:,.0f}",
            f"+${_expansion:,.0f}",
            f"-${abs(_churn):,.0f}",
            f"${_ending:,.0f}",
        ],
        textposition="outside",
        connector={"line": {"color": "#94A3B8"}},
        increasing={"marker": {"color": "#16A34A"}},
        decreasing={"marker": {"color": "#DC2626"}},
        totals={"marker": {"color": "#2563EB"}},
    ))
    fig_waterfall.update_layout(
        showlegend=False,
        yaxis_title="Monthly recurring revenue ($)",
        title=f"Net dollar retention waterfall — trailing 3 months ({_latest_3[0]} to {_latest_3[-1]})",
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)

    # ── Expansion velocity ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Expansion velocity — month-over-month growth")

    exp_vel = (
        revenue_df[revenue_df["motion"] == "Expansion"]
        .groupby("month")["MRR"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    exp_vel["mom_growth_pct"] = exp_vel["MRR"].pct_change() * 100
    exp_vel = exp_vel.dropna(subset=["mom_growth_pct"])

    fig_exp_vel = px.bar(
        exp_vel,
        x="month",
        y="mom_growth_pct",
        color="mom_growth_pct",
        color_continuous_scale=[[0, "#DC2626"], [0.5, "#94A3B8"], [1, "#16A34A"]],
        color_continuous_midpoint=0,
        range_color=[-60, 60],
        labels={"month": "Month", "mom_growth_pct": "Month-over-month growth (%)"},
    )
    fig_exp_vel.update_layout(coloraxis_showscale=False, showlegend=False)
    fig_exp_vel.add_hline(y=0, line_color="#0F172A", line_width=0.75)
    st.plotly_chart(fig_exp_vel, use_container_width=True)

    # ── Interpreting hours utilization ────────────────────────────────────────
    st.markdown("---")
    st.subheader("Interpreting hours utilization by service line")

    util_agg = (
        rev.groupby("service_line")[["utilized_hours", "contracted_hours"]]
        .sum()
        .reset_index()
    )
    util_melted = util_agg.melt(
        id_vars="service_line",
        value_vars=["utilized_hours", "contracted_hours"],
        var_name="type",
        value_name="hours",
    )
    util_melted["type"] = util_melted["type"].map({
        "utilized_hours": "Actual hours",
        "contracted_hours": "Contracted hours",
    })
    fig_util = px.bar(
        util_melted,
        x="service_line",
        y="hours",
        color="type",
        barmode="group",
        labels={"service_line": "Service line", "hours": "Hours", "type": ""},
        color_discrete_map={"Actual hours": "#2563EB", "Contracted hours": "#94A3B8"},
    )
    fig_util.update_layout(legend_title_text="")
    st.plotly_chart(fig_util, use_container_width=True)

    # ── Service level agreement compliance ────────────────────────────────────
    st.markdown("---")
    st.subheader("Service level agreement compliance by service line")

    sla_agg = (
        rev.groupby("service_line")["sla_met"]
        .mean()
        .reset_index()
        .rename(columns={"sla_met": "compliance_rate"})
    )
    fig_sla = px.bar(
        sla_agg,
        x="service_line",
        y="compliance_rate",
        labels={"service_line": "Service line", "compliance_rate": "Compliance rate"},
        color_discrete_sequence=["#2563EB"],
    )
    fig_sla.update_yaxes(tickformat=".0%", range=[0, 1.1])
    fig_sla.add_hline(
        y=0.95,
        line_dash="dash",
        line_color="#DC2626",
        annotation_text="95% target",
        annotation_position="top right",
    )
    st.plotly_chart(fig_sla, use_container_width=True)

# ── Tab 4: Rep Productivity and Compensation ──────────────────────────────────

with tab4:
    sel_territories = st.session_state.get("rep_territories", _ALL_TERRITORIES)
    reps_t4 = reps_df[reps_df["territory"].isin(sel_territories)].copy()

    # ── Quota vs attainment scatter ───────────────────────────────────────────
    st.subheader("Quota and attainment by rep")

    fig_scatter = px.scatter(
        reps_t4,
        x="quota",
        y="attainment_pct",
        color="territory",
        size="pipeline",
        hover_name="rep_name",
        hover_data={
            "win_rate": ":.1%",
            "avg_deal_size": ":$,.0f",
            "quota": ":$,.0f",
            "attainment_pct": ":.1%",
            "pipeline": ":$,.0f",
            "territory": False,
        },
        text="rep_name",
        labels={
            "quota": "Quota ($)",
            "attainment_pct": "Attainment",
            "territory": "Territory",
            "pipeline": "Pipeline ($)",
        },
    )
    fig_scatter.add_hline(
        y=1.0, line_dash="dash", line_color="#DC2626",
        annotation_text="100% quota", annotation_position="top right",
    )
    fig_scatter.add_hline(
        y=0.8, line_dash="dot", line_color="#D97706",
        annotation_text="80% floor", annotation_position="top right",
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_yaxes(tickformat=".0%")
    fig_scatter.update_xaxes(tickprefix="$", tickformat=",.0f")
    fig_scatter.update_layout(legend_title_text="Territory")
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Attainment tier breakdown ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Attainment tier breakdown")

    _TIER_ORDER = ["Below 50%", "50% to 79%", "80% to 99%", "100% and above"]
    _TIER_COLORS = {
        "Below 50%": "#DC2626", "50% to 79%": "#D97706",
        "80% to 99%": "#2563EB", "100% and above": "#16A34A",
    }

    def _tier(pct: float) -> str:
        if pct < 0.5: return "Below 50%"
        if pct < 0.8: return "50% to 79%"
        if pct < 1.0: return "80% to 99%"
        return "100% and above"

    tier_df = reps_t4.copy()
    tier_df["tier"] = tier_df["attainment_pct"].apply(_tier)
    tier_counts = tier_df.groupby("tier").size().reset_index(name="reps")
    tier_counts["tier"] = pd.Categorical(tier_counts["tier"], categories=_TIER_ORDER, ordered=True)
    tier_counts = tier_counts.sort_values("tier")

    fig_tiers = px.bar(
        tier_counts, x="tier", y="reps", color="tier",
        color_discrete_map=_TIER_COLORS,
        labels={"tier": "Attainment tier", "reps": "Number of reps"},
    )
    fig_tiers.update_layout(showlegend=False)
    fig_tiers.update_yaxes(dtick=1)
    st.plotly_chart(fig_tiers, use_container_width=True)

    # ── Days-in-stage heatmap ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Average days in stage per rep")

    open_t4 = pipeline_df[
        (~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])) &
        (pipeline_df["rep_name"].isin(reps_t4["rep_name"]))
    ]
    heatmap_pivot = (
        open_t4[open_t4["stage"].isin(_STAGE_ORDER)]
        .groupby(["rep_name", "stage"])["days_in_stage"]
        .mean().round(1).reset_index()
        .pivot(index="rep_name", columns="stage", values="days_in_stage")
        .reindex(columns=_STAGE_ORDER).fillna(0)
    )
    fig_heatmap = px.imshow(
        heatmap_pivot, color_continuous_scale="Blues",
        labels={"x": "Stage", "y": "Rep", "color": "Avg days"},
        aspect="auto", text_auto=".1f",
    )
    fig_heatmap.update_layout(xaxis_title="Stage", yaxis_title="", coloraxis_colorbar_title="Avg days")
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # ── Comp plan simulator ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Comp plan simulator")
    st.caption(
        "Adjust quota, tier thresholds, and the above-quota multiplier in the sidebar. "
        "The model updates in real time against every rep's actual attainment."
    )

    quota_adj_pct = st.session_state.get("quota_adj", 0) / 100
    floor = st.session_state.get("floor_pct", 50) / 100
    full_pay = st.session_state.get("full_pay_pct", 80) / 100
    accel = st.session_state.get("accel_mult", 1.25)

    comp = reps_t4.copy()
    comp["sim_quota"] = comp["quota"] * (1 + quota_adj_pct)
    comp["sim_attainment_pct"] = comp["attainment"] / comp["sim_quota"]
    comp["sim_bonus"] = comp.apply(
        lambda r: _sim_bonus(r["sim_attainment_pct"], r["variable_target"], floor, full_pay, accel),
        axis=1,
    )

    current_total = comp["calculated_bonus"].sum()
    sim_total = comp["sim_bonus"].sum()
    delta_pct = (sim_total - current_total) / current_total if current_total else 0
    current_at_quota = int((comp["attainment_pct"] >= 1.0).sum())
    sim_at_quota = int((comp["sim_attainment_pct"] >= 1.0).sum())
    sim_below_floor = int((comp["sim_attainment_pct"] < floor).sum())
    current_below_floor = int((comp["attainment_pct"] < 0.5).sum())

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Current commission expense", f"${current_total:,.0f}", border=True)
    with k2:
        st.metric(
            "Modeled commission expense", f"${sim_total:,.0f}",
            delta=f"{delta_pct:+.1%} vs current plan", delta_color="inverse", border=True,
        )
    with k3:
        st.metric(
            "Reps at or above quota", f"{sim_at_quota} of {len(comp)}",
            delta=f"{sim_at_quota - current_at_quota:+d} vs current plan", border=True,
        )
    with k4:
        st.metric(
            "Reps below payout floor", f"{sim_below_floor} of {len(comp)}",
            delta=f"{sim_below_floor - current_below_floor:+d} vs current plan",
            delta_color="inverse", border=True,
        )

    st.markdown("")

    comp_plot = comp[["rep_name", "calculated_bonus", "sim_bonus"]].sort_values("sim_bonus", ascending=False)
    comp_melted = comp_plot.melt(
        id_vars="rep_name", value_vars=["calculated_bonus", "sim_bonus"],
        var_name="plan", value_name="bonus",
    )
    comp_melted["plan"] = comp_melted["plan"].map({
        "calculated_bonus": "Current plan", "sim_bonus": "Modeled plan",
    })
    fig_comp = px.bar(
        comp_melted, x="rep_name", y="bonus", color="plan", barmode="group",
        color_discrete_map={"Current plan": "#94A3B8", "Modeled plan": "#2563EB"},
        labels={"rep_name": "Rep", "bonus": "Commission payout ($)", "plan": ""},
    )
    fig_comp.update_yaxes(tickprefix="$", tickformat=",.0f")
    fig_comp.update_layout(legend_title_text="")
    st.plotly_chart(fig_comp, use_container_width=True)

    # ── Variable compensation detail table ────────────────────────────────────
    st.markdown("---")
    st.subheader("Variable compensation detail")

    comp_table = comp[
        ["rep_name", "territory", "quota", "sim_quota", "attainment_pct",
         "sim_attainment_pct", "variable_target", "calculated_bonus", "sim_bonus"]
    ].copy().sort_values("sim_attainment_pct", ascending=False)
    comp_table["attainment_display"] = (comp_table["attainment_pct"] * 100).round(1)
    comp_table["sim_attainment_display"] = (comp_table["sim_attainment_pct"] * 100).round(1)
    comp_table["bonus_delta"] = comp_table["sim_bonus"] - comp_table["calculated_bonus"]

    st.dataframe(
        comp_table[[
            "rep_name", "territory", "quota", "sim_quota",
            "attainment_display", "sim_attainment_display",
            "variable_target", "calculated_bonus", "sim_bonus", "bonus_delta"
        ]],
        hide_index=True,
        use_container_width=True,
        column_config={
            "rep_name": "Rep",
            "territory": "Territory",
            "quota": st.column_config.NumberColumn("Current quota", format="$%.0f"),
            "sim_quota": st.column_config.NumberColumn("Modeled quota", format="$%.0f"),
            "attainment_display": st.column_config.NumberColumn("Current attainment", format="%.1f%%"),
            "sim_attainment_display": st.column_config.NumberColumn("Modeled attainment", format="%.1f%%"),
            "variable_target": st.column_config.NumberColumn("Variable target", format="$%.0f"),
            "calculated_bonus": st.column_config.NumberColumn("Current bonus", format="$%.0f"),
            "sim_bonus": st.column_config.NumberColumn("Modeled bonus", format="$%.0f"),
            "bonus_delta": st.column_config.NumberColumn("Delta", format="$%.0f"),
        },
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")

    if tab1.open:
        st.caption("No filters for this view.")

    elif tab2.open:
        st.radio(
            "Pipeline view", ["All deals", "Risk flagged only"],
            key="pipeline_view", horizontal=True,
        )
        st.caption("Risk flagged: deals past stage time limit, low engagement score, or discount above 20%.")

    elif tab3.open:
        st.multiselect("Service line", _ALL_SERVICE_LINES, default=_ALL_SERVICE_LINES, key="rev_service_lines")
        st.multiselect("Motion", _ALL_MOTIONS_REV, default=_ALL_MOTIONS_REV, key="rev_motions")
        st.select_slider(
            "Date range", options=_ALL_MONTHS,
            value=st.session_state["rev_month_range"], key="rev_month_range",
        )

    elif tab4.open:
        st.multiselect("Territory", _ALL_TERRITORIES, default=_ALL_TERRITORIES, key="rep_territories")
        st.divider()
        st.markdown("**Comp plan simulator**")
        st.slider("Quota adjustment", min_value=-20, max_value=30, value=0, step=1,
                  key="quota_adj", format="%d%%",
                  help="Shift all rep quotas up or down to model next year's plan")
        st.slider("Payout floor", min_value=40, max_value=70, value=50, step=5,
                  key="floor_pct", format="%d%%",
                  help="Minimum attainment required for any payout")
        st.slider("Full-pay threshold", min_value=70, max_value=90, value=80, step=5,
                  key="full_pay_pct", format="%d%%",
                  help="Attainment at which 100% of variable target is earned")
        st.slider("Above-quota multiplier", min_value=1.0, max_value=2.0, value=1.25, step=0.05,
                  key="accel_mult",
                  help="Multiplier applied to variable target for above-quota attainment")

    else:
        st.caption("Select a tab to see filters.")
