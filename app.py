import streamlit as st
import pandas as pd

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

with tab1:
    st.write("Tab 1 coming soon.")

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
        response = "Chatbot not yet connected."
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        messages.chat_message("assistant").write(response)
