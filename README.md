# Sorenson RevOps Center

[![View Live Dashboard](https://img.shields.io/badge/View%20Live%20Dashboard-%23FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://senior-sales-operations-analyst.streamlit.app/)

A production-deployed revenue operations intelligence dashboard built to demonstrate Senior Sales Operations readiness at Sorenson Communications.

---

## From Scaffold to Production

This repo is a fork of [@munas-git's AI-Powered Sales KPI Dashboard](https://github.com/munas-git/AI-powered-sales-dashboard). The original served as the wireframe. This is the build.

The following were stripped out by design:

- **MongoDB and pyodbc** — replaced with a lightweight CSV-native data layer. Three flat files (pipeline.csv, revenue.csv, reps.csv) remove all infrastructure dependency and make the app fully portable on Streamlit Community Cloud.
- **LangChain, RAG agent, and OpenAI chatbot** — removed entirely. A live API dependency introduces failure risk in a demo context; the analytical depth of the dashboard carries the demonstration without it.
- **Generic sales data** — replaced with synthetic data modeled on Sorenson Communications' five service lines, SLA structure, and three-motion revenue operation (New, Expand, Renew) — the analytical patterns of any enterprise interpreting services business, built with Sorenson's specific context by name.

Forking, stripping, and rebuilding a scaffold is a deliberate product judgment call. Every removal was a decision about what actually serves the purpose.

---

## Four-Tab Architecture

| Tab | Title | Core Business Question |
|-----|-------|------------------------|
| 1 | Executive Summary | How is the business performing right now at a glance? |
| 2 | Pipeline & Forecast | Which deals are at risk and what will we close this quarter? |
| 3 | Multi-Motion Revenue | How are our service lines and sales motions trending? |
| 4 | Rep Productivity & Compensation | Who is performing, who needs coaching, and are reps paid fairly? |

---

## Key Features

- **Risk-adjusted forecasting** — composite deal risk scoring (stage overage, risk flags, deal size) feeding three forecast scenarios: conservative, base, and upside. Built to replace gut-feel pipeline calls with a reproducible, stage-weighted model.
- **Pipeline hygiene tracking** — at-risk deal table with four boolean hygiene fields (past stage benchmark, high discount, low engagement, manual risk flag) modeled after the fields a Dynamics 365 CRM admin would track.
- **Consumption velocity cohort matrix** — utilization heatmap showing how much of their contracted interpreting hours each customer cohort consumes by month of tenure. Red cells at month 3 signal churn risk before month 12 renewal.
- **Compensation plan simulator** — four-tier commission logic (floor, ramp, at-quota, accelerator) with real-time payout calculation at any attainment level, including the floor cliff edge case that generates the most rep disputes.

---

## Data

Three synthetic CSV files in the `/data` folder. Fixed random seed (42) ensures reproducibility across every run.

| File | Rows | Contents |
|------|------|----------|
| pipeline.csv | 135 deals | deal_id, rep, territory, motion, stage, ARR, days_in_stage, risk flags |
| revenue.csv | 480 rows | 8 service lines × 60 months, MRR, contracted hours, utilized hours, SLA met |
| reps.csv | 12 reps | quota, attainment, win rate, avg deal size, days to close, bonus, TAM |

The data is simulated. The logic — formulas, risk scoring, compensation tiers, cohort structure — is production-ready.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| App framework | Python 3.12 + Streamlit |
| Visualization | Plotly Express + Graph Objects |
| Data processing | pandas + NumPy |
| Deployment | Streamlit Community Cloud |
| Version control | GitHub (auto-deploys from main) |
| Data | CSV (3 files, no database) |

---

## Getting Started

```bash
git clone https://github.com/datadynamo-hub/Senior-Sales-Operations-Analyst.git
cd Senior-Sales-Operations-Analyst
```

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

---

Built by Jonathan Khan for Sorenson Communications interview preparation.
