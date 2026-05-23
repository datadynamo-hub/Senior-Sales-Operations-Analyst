import streamlit as st
import pandas as pd
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

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Executive Summary",
        "Pipeline and Forecast",
        "Multi-Motion Revenue",
        "Rep Productivity and Compensation",
        "Fill This Out",
    ],
    on_change="rerun",
)

# ── Tab 1: Executive Summary ──────────────────────────────────────────────────

with tab1:
    open_deals = pipeline_df[~pipeline_df["stage"].isin(["Closed Won", "Closed Lost"])]

    # Pipeline coverage ratio
    total_pipeline = open_deals["ARR"].sum()
    total_quota = reps_df["quota"].sum()
    coverage = total_pipeline / total_quota

    # Net dollar retention (trailing 3 months)
    latest_months = sorted(revenue_df["month"].unique())[-3:]
    qtd = revenue_df[revenue_df["month"].isin(latest_months)]
    renewal_mrr = qtd[qtd["motion"] == "Renewal"]["MRR"].sum()
    expansion_mrr = qtd[qtd["motion"] == "Expansion"]["MRR"].sum()
    churn_mrr = qtd[qtd["motion"] == "Churn"]["MRR"].sum()
    ndr = (renewal_mrr + expansion_mrr + churn_mrr) / renewal_mrr if renewal_mrr else 0
    expansion_rate = expansion_mrr / renewal_mrr if renewal_mrr else 0
    contraction_rate = churn_mrr / renewal_mrr if renewal_mrr else 0

    # Quota attainment
    reps_above_80 = int((reps_df["attainment_pct"] >= 0.80).sum())
    total_reps = len(reps_df)

    # Service level agreement compliance
    sla_rate = revenue_df["sla_met"].mean()

    # Interpreting hours utilization
    util_rate = (
        revenue_df["utilized_hours"].sum() / revenue_df["contracted_hours"].sum()
    )

    # Deal velocity (average days in stage by motion)
    velocity_new = open_deals[open_deals["motion"] == "New"]["days_in_stage"].mean()
    velocity_renewal = open_deals[open_deals["motion"] == "Renewal"]["days_in_stage"].mean()

    # KPI row
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

    # Deal velocity
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

with tab2:
    st.write("Tab 2 coming soon.")

with tab3:
    st.write("Tab 3 coming soon.")

with tab4:
    st.write("Tab 4 coming soon.")

with tab5:
    pass

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")

    if tab1.open:
        st.caption("No filters for this view.")
    elif tab2.open:
        st.caption("Pipeline filters — coming soon.")
    elif tab3.open:
        st.caption("Revenue filters — coming soon.")
    elif tab4.open:
        st.caption("Rep filters — coming soon.")
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
