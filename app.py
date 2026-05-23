import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from agent import Agent

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

# ── Data summary for chatbot system prompt ────────────────────────────────────

@st.cache_data
def build_system_prompt(pipeline: pd.DataFrame, revenue: pd.DataFrame, reps: pd.DataFrame) -> str:
    total_arr = pipeline["ARR"].sum()
    risk_count = pipeline["risk_flag"].sum()
    motion_arr = pipeline.groupby("motion")["ARR"].sum().to_dict()

    latest_month = revenue["month"].max()
    rev_latest = revenue[revenue["month"] == latest_month]
    ndr_components = rev_latest.groupby("motion")["MRR"].sum().to_dict()

    util = revenue.groupby("service_line").apply(
        lambda x: (x["utilized_hours"].sum() / x["contracted_hours"].sum())
    ).round(3).to_dict()

    avg_attainment = reps["attainment_pct"].mean()
    reps_above_80 = (reps["attainment_pct"] >= 0.80).sum()
    most_risk = pipeline[pipeline["risk_flag"]].groupby("rep_name").size().idxmax()

    return f"""You are an AI assistant embedded in the Sorenson RevOps Center dashboard.
Answer questions only about the pipeline, forecast, revenue, and rep performance data shown below.
Do not answer general knowledge questions. Be concise and specific.

PIPELINE SUMMARY (open deals):
- Total open pipeline annual recurring revenue: ${total_arr:,.0f}
- Deals with risk flags: {risk_count} of {len(pipeline)}
- Pipeline by motion: New ${motion_arr.get('New', 0):,.0f} | Expansion ${motion_arr.get('Expansion', 0):,.0f} | Renewal ${motion_arr.get('Renewal', 0):,.0f}
- Rep with most risk-flagged deals: {most_risk}

REVENUE SUMMARY (latest month: {latest_month}):
- New motion monthly recurring revenue: ${ndr_components.get('New', 0):,.0f}
- Expansion monthly recurring revenue: ${ndr_components.get('Expansion', 0):,.0f}
- Renewal monthly recurring revenue: ${ndr_components.get('Renewal', 0):,.0f}
- Churn monthly recurring revenue: ${ndr_components.get('Churn', 0):,.0f}

HOURS UTILIZATION BY SERVICE LINE:
{chr(10).join(f"- {sl}: {rate:.0%}" for sl, rate in util.items())}

REP PERFORMANCE:
- Average quota attainment: {avg_attainment:.0%}
- Reps at or above 80% attainment: {reps_above_80} of {len(reps)}
"""

system_prompt = build_system_prompt(pipeline_df, revenue_df, reps_df)

# ── Agent ─────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_agent(prompt: str) -> Agent:
    return Agent(system_prompt=prompt)

agent = get_agent(system_prompt)

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

# ── Shared constants ──────────────────────────────────────────────────────────

_MOTION_COLORS = {
    "New": "#2563EB",
    "Expansion": "#16A34A",
    "Renewal": "#D97706",
    "Churn": "#DC2626",
}

_ALL_SERVICE_LINES = sorted(revenue_df["service_line"].unique().tolist())
_ALL_MOTIONS_REV = sorted(m for m in revenue_df["motion"].unique() if m != "Churn")
_ALL_MONTHS = sorted(revenue_df["month"].unique().tolist())
_ALL_TERRITORIES = sorted(reps_df["territory"].unique().tolist())

# ── Session state defaults ────────────────────────────────────────────────────

if "pipeline_view" not in st.session_state:
    st.session_state["pipeline_view"] = "All deals"
if "rev_service_lines" not in st.session_state:
    st.session_state["rev_service_lines"] = _ALL_SERVICE_LINES
if "rev_motions" not in st.session_state:
    st.session_state["rev_motions"] = _ALL_MOTIONS_REV
if "rev_month_range" not in st.session_state:
    st.session_state["rev_month_range"] = (_ALL_MONTHS[0], _ALL_MONTHS[-1])
if "rep_territories" not in st.session_state:
    st.session_state["rep_territories"] = _ALL_TERRITORIES

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

    util_rate = (
        revenue_df["utilized_hours"].sum() / revenue_df["contracted_hours"].sum()
    )

    velocity_new = open_deals[open_deals["motion"] == "New"]["days_in_stage"].mean()
    velocity_renewal = open_deals[open_deals["motion"] == "Renewal"]["days_in_stage"].mean()

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

    st.markdown("---")
    st.subheader("Average Deal Velocity")
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

# ── Tab 2: Pipeline and Forecast ──────────────────────────────────────────────

with tab2:
    _STAGE_ORDER = ["Prospect", "Qualified", "Demo", "Proposal", "Negotiation"]

    open_t2 = pipeline_df[~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])].copy()

    view = st.session_state.get("pipeline_view", "All deals")
    filtered = open_t2[open_t2["risk_flag"]] if view == "Risk flagged only" else open_t2

    st.subheader("Open pipeline by stage and motion")

    funnel_data = (
        filtered[filtered["stage"].isin(_STAGE_ORDER)]
        .groupby(["stage", "motion"])
        .size()
        .reset_index(name="deal_count")
    )
    funnel_data["stage"] = pd.Categorical(
        funnel_data["stage"], categories=_STAGE_ORDER, ordered=True
    )
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

    st.markdown("---")
    st.subheader("Average days in stage by motion")

    velocity = (
        open_t2.groupby(["stage", "motion"])["days_in_stage"]
        .mean()
        .round(1)
        .reset_index()
    )
    velocity["stage"] = pd.Categorical(
        velocity["stage"], categories=_STAGE_ORDER, ordered=True
    )
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

    st.markdown("---")
    st.subheader("Deal list by rep")

    deal_list = filtered[
        ["rep_name", "motion", "stage", "ARR", "close_date", "risk_flag"]
    ].copy()
    deal_list = deal_list.sort_values(
        ["risk_flag", "close_date"], ascending=[False, True]
    )

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
            "risk_flag": st.column_config.CheckboxColumn("Risk flag"),
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
        labels={
            "month": "Month",
            "MRR": "Monthly recurring revenue ($)",
            "motion": "Motion",
        },
        color_discrete_map=_MOTION_COLORS,
    )
    fig_mrr.update_layout(legend_title_text="Motion")
    st.plotly_chart(fig_mrr, use_container_width=True)

    # ── Net dollar retention waterfall ────────────────────────────────────────
    st.markdown("---")
    st.subheader("Net dollar retention waterfall (trailing 3 months)")

    _latest_3 = sorted(revenue_df["month"].unique())[-3:]
    _wf = revenue_df[revenue_df["month"].isin(_latest_3)]

    _renewal = _wf[_wf["motion"] == "Renewal"]["MRR"].sum()
    _expansion = _wf[_wf["motion"] == "Expansion"]["MRR"].sum()
    _churn = _wf[_wf["motion"] == "Churn"]["MRR"].sum()   # already negative
    _ending = _renewal + _expansion + _churn
    _ndr = _ending / _renewal if _renewal else 0

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
        title=f"Net dollar retention: {_ndr:.1%}",
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)

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
        color_discrete_map={
            "Actual hours": "#2563EB",
            "Contracted hours": "#94A3B8",
        },
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
        y=1.0,
        line_dash="dash",
        line_color="#DC2626",
        annotation_text="100% quota",
        annotation_position="top right",
    )
    fig_scatter.add_hline(
        y=0.8,
        line_dash="dot",
        line_color="#D97706",
        annotation_text="80% floor",
        annotation_position="top right",
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
        "Below 50%": "#DC2626",
        "50% to 79%": "#D97706",
        "80% to 99%": "#2563EB",
        "100% and above": "#16A34A",
    }

    def _tier(pct: float) -> str:
        if pct < 0.5:
            return "Below 50%"
        if pct < 0.8:
            return "50% to 79%"
        if pct < 1.0:
            return "80% to 99%"
        return "100% and above"

    tier_df = reps_t4.copy()
    tier_df["tier"] = tier_df["attainment_pct"].apply(_tier)
    tier_counts = tier_df.groupby("tier").size().reset_index(name="reps")
    tier_counts["tier"] = pd.Categorical(
        tier_counts["tier"], categories=_TIER_ORDER, ordered=True
    )
    tier_counts = tier_counts.sort_values("tier")

    fig_tiers = px.bar(
        tier_counts,
        x="tier",
        y="reps",
        color="tier",
        color_discrete_map=_TIER_COLORS,
        labels={"tier": "Attainment tier", "reps": "Number of reps"},
    )
    fig_tiers.update_layout(showlegend=False)
    fig_tiers.update_yaxes(dtick=1)
    st.plotly_chart(fig_tiers, use_container_width=True)

    # ── Days-in-stage heatmap per rep ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("Average days in stage per rep")

    open_t4 = pipeline_df[
        (~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])) &
        (pipeline_df["rep_name"].isin(reps_t4["rep_name"]))
    ]

    heatmap_pivot = (
        open_t4[open_t4["stage"].isin(_STAGE_ORDER)]
        .groupby(["rep_name", "stage"])["days_in_stage"]
        .mean()
        .round(1)
        .reset_index()
        .pivot(index="rep_name", columns="stage", values="days_in_stage")
        .reindex(columns=_STAGE_ORDER)
        .fillna(0)
    )

    fig_heatmap = px.imshow(
        heatmap_pivot,
        color_continuous_scale="Blues",
        labels={"x": "Stage", "y": "Rep", "color": "Avg days"},
        aspect="auto",
        text_auto=".1f",
    )
    fig_heatmap.update_layout(
        xaxis_title="Stage",
        yaxis_title="",
        coloraxis_colorbar_title="Avg days",
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # ── Variable compensation summary ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("Variable compensation summary")

    comp_table = reps_t4[
        ["rep_name", "territory", "quota", "attainment_pct",
         "base", "variable_target", "calculated_bonus"]
    ].copy().sort_values("attainment_pct", ascending=False)

    comp_table["attainment_display"] = (comp_table["attainment_pct"] * 100).round(1)

    st.dataframe(
        comp_table.drop(columns=["attainment_pct"]),
        hide_index=True,
        use_container_width=True,
        column_config={
            "rep_name": "Rep",
            "territory": "Territory",
            "quota": st.column_config.NumberColumn("Quota", format="$%.0f"),
            "attainment_display": st.column_config.NumberColumn("Attainment", format="%.1f%%"),
            "base": st.column_config.NumberColumn("Base salary", format="$%.0f"),
            "variable_target": st.column_config.NumberColumn("Variable target", format="$%.0f"),
            "calculated_bonus": st.column_config.NumberColumn("Calculated bonus", format="$%.0f"),
        },
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")

    if tab1.open:
        st.caption("No filters for this view.")
    elif tab2.open:
        st.radio(
            "Pipeline view",
            ["All deals", "Risk flagged only"],
            key="pipeline_view",
            horizontal=True,
        )
        st.caption(
            "Risk flagged: deals past stage time limit, low engagement score, "
            "or discount above 20%."
        )
    elif tab3.open:
        st.multiselect(
            "Service line",
            _ALL_SERVICE_LINES,
            default=_ALL_SERVICE_LINES,
            key="rev_service_lines",
        )
        st.multiselect(
            "Motion",
            _ALL_MOTIONS_REV,
            default=_ALL_MOTIONS_REV,
            key="rev_motions",
        )
        st.select_slider(
            "Date range",
            options=_ALL_MONTHS,
            value=st.session_state["rev_month_range"],
            key="rev_month_range",
        )
    elif tab4.open:
        st.multiselect(
            "Territory",
            _ALL_TERRITORIES,
            default=_ALL_TERRITORIES,
            key="rep_territories",
        )
    else:
        st.caption("Select a tab to see filters.")

    st.divider()
    st.header("AI Assistant")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    messages = st.container(height=300)
    for msg in st.session_state.chat_messages:
        messages.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Ask about the data..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        messages.chat_message("user").write(prompt)
        response = agent.answer(st.session_state.chat_messages)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        messages.chat_message("assistant").write(response)
