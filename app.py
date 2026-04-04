import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from mistralai.client import Mistral
from data import df_raw, MONTH_ORDER

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Summit Line Construction Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────
COLORS = {
    "primary":   "#2E86AB",
    "secondary": "#A8DADC",
    "dark":      "#1B4965",
    "accent":    "#F4A261",
    "danger":    "#E63946",
    "success":   "#2DC653",
    "warning":   "#FFB703",
    "bg":        "#F0F4F8",
    "card":      "#FFFFFF",
    "text":      "#1B2631",
    "muted":     "#7F8C8D",
}

STATUS_COLORS = {
    "Planning":    COLORS["primary"],
    "In Progress": COLORS["warning"],
    "On Hold":     COLORS["danger"],
    "Completed":   COLORS["success"],
}

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* White page background */
    .main, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="block-container"] {
        background-color: #ffffff !important;
    }

    /* Keep sidebar dark and always visible */
    [data-testid="stSidebar"] {
        background-color: #1B2631 !important;
        min-width: 240px !important;
        max-width: 240px !important;
        transform: none !important;
        visibility: visible !important;
    }
    [data-testid="stSidebar"] * { color: white !important; }

    /* Hide ALL collapse/expand buttons (multiple selectors for v1.56 compat) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="open sidebar"],
    button[aria-label="Open sidebar"],
    section[data-testid="stSidebar"] button,
    [data-testid="stSidebarNav"] { display: none !important; }

    [data-testid="stSidebar"] .stRadio > label { display: none; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        padding: 10px 16px !important;
        border-radius: 6px !important;
        margin: 2px 0 !important;
        font-size: 14px !important;
        cursor: pointer !important;
        display: block !important;
        transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(46,134,171,0.3) !important;
    }

    /* KPI cards */
    .kpi-card {
        background: white; border-radius: 8px; padding: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.10); text-align: center;
        border-top: 4px solid #2E86AB;
    }
    .kpi-value { font-size: 32px; font-weight: 800; color: #1B4965; }
    .kpi-label { font-size: 13px; color: #2E86AB; font-weight: 600; margin-top: 4px; }

    /* Chart / filter cards */
    .chart-card {
        background: white; border-radius: 8px; padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.10); margin-bottom: 12px;
    }
    .filter-bar {
        background: white; padding: 12px; border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.10); margin-bottom: 16px;
    }

    /* Hide streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    .stSelectbox label {
        font-size: 11px !important; font-weight: 700 !important;
        color: #555 !important; text-transform: uppercase;
    }
    div[data-testid="stHorizontalBlock"] { gap: 12px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def style_chart(fig, title, height=320):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#1B2631", family="Arial"), x=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial", size=12, color="#1B2631"),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#1B2631")),
        xaxis=dict(showgrid=True, gridcolor="#E0E0E0", zeroline=False,
                   tickfont=dict(color="#1B2631"), title_font=dict(color="#1B2631")),
        yaxis=dict(showgrid=True, gridcolor="#E0E0E0", zeroline=False,
                   tickfont=dict(color="#1B2631"), title_font=dict(color="#1B2631")),
        height=height,
    )
    return fig


def kpi_card(label, value, color="#2E86AB"):
    return f"""
    <div class="kpi-card" style="border-top-color:{color};">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""


def render_kpi_row(cards):
    cols = st.columns(len(cards))
    for col, (label, value, color) in zip(cols, cards):
        with col:
            st.markdown(kpi_card(label, value, color), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────
def render_filters(df):
    filter_fields = ["Region", "Status", "Project Type", "Phase", "Department", "Contractor", "Budget Status"]
    cols = st.columns(len(filter_fields))
    filters = {}
    for i, field in enumerate(filter_fields):
        with cols[i]:
            options = ["All"] + sorted(df[field].unique().tolist())
            filters[field] = st.selectbox(field, options, key=f"filter_{field}")
    return filters


def apply_filters(df, filters):
    filtered = df.copy()
    for field, val in filters.items():
        if val != "All":
            filtered = filtered[filtered[field] == val]
    return filtered


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='background:#1B4965; padding:20px; border-radius:8px;
                    text-align:center; margin-bottom:20px;'>
            <h2 style='color:#F4A261; margin:0; font-size:28px;'>⚡</h2>
            <h3 style='color:white; margin:5px 0 0 0; font-size:14px;'>Summit Line Construction</h3>
            <p style='color:#A8DADC; font-size:11px; margin:0;'>Project Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        pages = [
            "📊 Overview",
            "💰 Budget vs Cost",
            "🏗️ Contractor & Department",
            "🦺 Safety & Risk",
            "📅 Monthly Trend",
            "🔍 Decomposition View",
            "🤖 AI Assistant",
        ]
        selected = st.radio("Navigation", pages, label_visibility="collapsed")

        st.markdown("---")
        st.markdown(
            "<p style='font-size:10px; color:#7F8C8D; text-align:center;'>"
            "Built with Mistral AI · Summit Line Construction</p>",
            unsafe_allow_html=True,
        )
    return selected


# ─────────────────────────────────────────────
# PAGE 1: OVERVIEW
# ─────────────────────────────────────────────
def page_overview(df):
    n_projects = len(df)
    total_budget = df["Budget"].sum() / 1_000
    total_cost = df["Cost"].sum() / 1_000
    cost_per_proj = (df["Cost"].mean() / 1_000) if n_projects else 0
    total_incidents = int(df["Safety Incidents"].sum())

    render_kpi_row([
        ("# of Projects", f"{n_projects:,}", COLORS["primary"]),
        ("Total Budget", f"${total_budget:,.2f}K", COLORS["dark"]),
        ("Total Cost", f"${total_cost:,.2f}K", COLORS["secondary"].replace("A8DADC", "2E86AB")),
        ("Cost Per Project", f"${cost_per_proj:,.1f}K", COLORS["accent"]),
        ("Safety Incidents", f"{total_incidents:,}", COLORS["danger"]),
    ])

    # Row 1 — 3 charts
    c1, c2, c3 = st.columns(3)

    with c1:
        reg = df.groupby("Region").size().reset_index(name="Count").sort_values("Count")
        fig = go.Figure(go.Bar(
            x=reg["Count"], y=reg["Region"], orientation="h",
            marker_color=COLORS["primary"],
            text=reg["Count"], textposition="outside",
        ))
        style_chart(fig, "# of Projects by Region")
        fig.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True, gridcolor="#F0F4F8"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        stat = df.groupby("Status").size().reset_index(name="Count")
        colors_pie = [STATUS_COLORS.get(s, COLORS["muted"]) for s in stat["Status"]]
        fig = go.Figure(go.Pie(
            labels=stat["Status"], values=stat["Count"],
            hole=0.45,
            marker=dict(colors=colors_pie),
            textinfo="label+percent",
            textfont_size=11,
        ))
        style_chart(fig, "# of Projects by Status")
        fig.update_layout(legend=dict(orientation="v", x=1, y=0.5))
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        phase_order = ["Foundation", "Finishing", "Design", "Structure", "Closeout"]
        ph = df.groupby("Phase").size().reset_index(name="Count")
        ph["Phase"] = pd.Categorical(ph["Phase"], categories=phase_order, ordered=True)
        ph = ph.sort_values("Phase")
        fig = go.Figure(go.Bar(
            x=ph["Phase"], y=ph["Count"],
            marker_color=COLORS["primary"],
            text=ph["Count"], textposition="outside",
        ))
        style_chart(fig, "# of Projects by Phase")
        st.plotly_chart(fig, use_container_width=True)

    # Row 2 — line + bar
    c4, c5 = st.columns([2, 1])

    with c4:
        monthly = df.groupby(["Month", "Month_Num"]).size().reset_index(name="Count")
        monthly = monthly.sort_values("Month_Num")
        monthly["Month"] = pd.Categorical(monthly["Month"], categories=MONTH_ORDER, ordered=True)
        monthly = monthly.sort_values("Month")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["Month"], y=monthly["Count"],
            marker_color=COLORS["secondary"],
            name="Projects",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["Month"], y=monthly["Count"],
            mode="lines+markers+text",
            line=dict(color=COLORS["dark"], width=2),
            marker=dict(size=8, color=COLORS["accent"], symbol="circle"),
            text=monthly["Count"], textposition="top center",
            name="Trend",
        ))
        style_chart(fig, "# of Projects by Month")
        st.plotly_chart(fig, use_container_width=True)

    with c5:
        cpp = df.groupby("Project Type")["Cost"].mean().reset_index()
        cpp.columns = ["Project Type", "Avg Cost"]
        cpp = cpp.sort_values("Avg Cost", ascending=False)
        fig = go.Figure(go.Bar(
            x=cpp["Project Type"], y=cpp["Avg Cost"],
            marker_color=COLORS["primary"],
            text=[f"${v/1000:.1f}K" for v in cpp["Avg Cost"]],
            textposition="outside",
        ))
        style_chart(fig, "Cost Per Project by Project Type")
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE 2: BUDGET VS COST
# ─────────────────────────────────────────────
def page_budget_vs_cost(df):
    c1, c2, c3 = st.columns(3)

    # By Department
    with c1:
        dept_grp = df.groupby("Department").agg(Budget=("Budget", "sum"), Cost=("Cost", "sum")).reset_index()
        dept_grp = dept_grp.sort_values("Budget")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=dept_grp["Department"], x=dept_grp["Budget"],
            orientation="h", name="Budget",
            marker_color=COLORS["dark"],
            text=[f"${v/1000:.2f}M" for v in dept_grp["Budget"]],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            y=dept_grp["Department"], x=dept_grp["Cost"],
            orientation="h", name="Cost",
            marker_color=COLORS["secondary"],
            text=[f"${v/1000:.2f}M" for v in dept_grp["Cost"]],
            textposition="outside",
        ))
        fig.update_layout(barmode="group")
        style_chart(fig, "Budget and Cost by Department")
        st.plotly_chart(fig, use_container_width=True)

    # By Project Type
    with c2:
        pt_grp = df.groupby("Project Type").agg(Budget=("Budget", "sum"), Cost=("Cost", "sum")).reset_index()
        pt_grp = pt_grp.sort_values("Budget", ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pt_grp["Project Type"], y=pt_grp["Budget"],
            name="Budget", marker_color=COLORS["dark"],
            text=[f"${v/1000:.2f}M" for v in pt_grp["Budget"]],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            x=pt_grp["Project Type"], y=pt_grp["Cost"],
            name="Cost", marker_color=COLORS["secondary"],
            text=[f"${v/1000:.2f}M" for v in pt_grp["Cost"]],
            textposition="outside",
        ))
        fig.update_layout(barmode="group")
        style_chart(fig, "Budget and Cost by Project Type")
        st.plotly_chart(fig, use_container_width=True)

    # By Region
    with c3:
        reg_grp = df.groupby("Region").agg(Budget=("Budget", "sum"), Cost=("Cost", "sum")).reset_index()
        reg_grp = reg_grp.sort_values("Budget")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=reg_grp["Region"], x=reg_grp["Budget"],
            orientation="h", name="Budget",
            marker_color=COLORS["dark"],
            text=[f"${v/1000:.2f}M" for v in reg_grp["Budget"]],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            y=reg_grp["Region"], x=reg_grp["Cost"],
            orientation="h", name="Cost",
            marker_color=COLORS["secondary"],
            text=[f"${v/1000:.2f}M" for v in reg_grp["Cost"]],
            textposition="outside",
        ))
        fig.update_layout(barmode="group")
        style_chart(fig, "Budget and Cost by Region")
        st.plotly_chart(fig, use_container_width=True)

    # Full-width — top 7 contractors
    top7 = (df.groupby("Contractor")
              .agg(Budget=("Budget", "sum"), Cost=("Cost", "sum"))
              .reset_index()
              .sort_values("Budget", ascending=False)
              .head(7))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top7["Contractor"], y=top7["Budget"],
        name="Budget", marker_color=COLORS["dark"],
        text=[f"${v/1000:.0f}K" for v in top7["Budget"]],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=top7["Contractor"], y=top7["Cost"],
        name="Cost", marker_color=COLORS["secondary"],
        text=[f"${v/1000:.0f}K" for v in top7["Cost"]],
        textposition="outside",
        textfont=dict(color="#1B2631"),
    ))
    fig.add_trace(go.Scatter(
        x=top7["Contractor"], y=top7["Cost"],
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=2, dash="solid"),
        marker=dict(size=8, color=COLORS["accent"]),
        name="Cost Trend",
    ))
    fig.update_layout(barmode="group")
    style_chart(fig, "Budget and Cost by Top 7 Contractors", height=380)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE 3: CONTRACTOR & DEPARTMENT
# ─────────────────────────────────────────────
def page_contractor_dept(df):
    c1, c2, c3 = st.columns(3)

    with c1:
        top7 = (df.groupby("Contractor").size().reset_index(name="Count")
                  .sort_values("Count", ascending=False).head(7)
                  .sort_values("Count"))
        fig = go.Figure(go.Bar(
            y=top7["Contractor"], x=top7["Count"],
            orientation="h", marker_color=COLORS["primary"],
            text=top7["Count"], textposition="outside",
        ))
        style_chart(fig, "# of Projects by Top 7 Contractor")
        fig.update_layout(yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        dept = df.groupby("Department").size().reset_index(name="Count")
        fig = px.treemap(
            dept, path=["Department"], values="Count",
            color="Count",
            color_continuous_scale=[[0, COLORS["secondary"]], [1, COLORS["dark"]]],
        )
        fig.update_traces(textinfo="label+value", textfont_size=14)
        style_chart(fig, "# of Projects by Department")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        top7_si = (df.groupby("Contractor")["Safety Incidents"].sum()
                     .reset_index()
                     .sort_values("Safety Incidents", ascending=False)
                     .head(7))
        fig = go.Figure(go.Bar(
            x=top7_si["Contractor"], y=top7_si["Safety Incidents"],
            marker_color=COLORS["text"],
            text=top7_si["Safety Incidents"], textposition="outside",
        ))
        style_chart(fig, "Safety Incidents by Top 7 Contractor")
        fig.update_layout(xaxis=dict(tickangle=-30))
        st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.markdown("### Project Detail")
    table_df = df[["ID", "Project Name", "Project Type", "Region", "Status",
                   "Contractor", "Department", "Budget", "Cost"]].copy()
    table_df["Budget"] = table_df["Budget"].apply(lambda x: f"${x:,.1f}")
    table_df["Cost_raw"] = df["Cost"]
    table_df["Budget_raw"] = df["Budget"]

    def color_cost(row):
        styles = [""] * len(row)
        cost_idx = list(row.index).index("Cost")
        if row["Cost_raw"] > row["Budget_raw"]:
            styles[cost_idx] = "color: #E63946; font-weight:bold"
        else:
            styles[cost_idx] = "color: #2DC653; font-weight:bold"
        return styles

    display_df = table_df.drop(columns=["Cost_raw", "Budget_raw"])
    display_df["Cost"] = df["Cost"].apply(lambda x: f"${x:,.1f}")

    st.dataframe(display_df, use_container_width=True, height=350)


# ─────────────────────────────────────────────
# PAGE 4: SAFETY & RISK
# ─────────────────────────────────────────────
def page_safety_risk(df):
    total_incidents = int(df["Safety Incidents"].sum())
    over_budget = (df["Budget Status"] == "Over Budget").sum()
    over_pct = over_budget / len(df) * 100 if len(df) else 0
    avg_sched_var = df["Schedule Variance (%)"].mean()
    total_rfis = int(df["RFIs Open"].sum())
    total_co = int(df["Change Orders"].sum())

    render_kpi_row([
        ("Safety Incidents", f"{total_incidents:,}", COLORS["danger"]),
        ("Projects Over Budget", f"{over_budget} ({over_pct:.0f}%)", COLORS["accent"]),
        ("Avg Schedule Variance", f"{avg_sched_var:+.1f}%", COLORS["warning"]),
        ("Total Open RFIs", f"{total_rfis:,}", COLORS["primary"]),
        ("Total Change Orders", f"{total_co:,}", COLORS["dark"]),
    ])

    c1, c2, c3 = st.columns(3)

    with c1:
        reg_si = (df.groupby("Region")["Safety Incidents"].sum()
                    .reset_index().sort_values("Safety Incidents"))
        fig = go.Figure(go.Bar(
            y=reg_si["Region"], x=reg_si["Safety Incidents"],
            orientation="h", marker_color=COLORS["danger"],
            text=reg_si["Safety Incidents"], textposition="outside",
        ))
        style_chart(fig, "Safety Incidents by Region")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        bs = df["Budget Status"].value_counts().reset_index()
        bs.columns = ["Status", "Count"]
        fig = go.Figure(go.Pie(
            labels=bs["Status"], values=bs["Count"],
            hole=0.4,
            marker=dict(colors=[COLORS["success"], COLORS["danger"]]),
            textinfo="label+percent",
        ))
        style_chart(fig, "Budget Status Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        df_risk = df.copy()
        df_risk["Budget Burn %"] = (df_risk["Cost"] / df_risk["Budget"] * 100).clip(0, 150)
        df_risk["Risk"] = df_risk.apply(
            lambda r: "Critical" if r["Budget Burn %"] > 110 and r["Schedule Variance (%)"] > 10
            else "High" if r["Budget Burn %"] > 100 or r["Schedule Variance (%)"] > 10
            else "Medium" if r["Budget Burn %"] > 90
            else "Low", axis=1)
        risk_colors = {"Critical": COLORS["danger"], "High": COLORS["accent"],
                       "Medium": COLORS["warning"], "Low": COLORS["success"]}
        fig = px.scatter(
            df_risk, x="Schedule Variance (%)", y="Budget Burn %",
            size="Crew Size", color="Risk",
            color_discrete_map=risk_colors,
            hover_name="Project Name",
            hover_data=["Contractor", "Region"],
            opacity=0.7,
        )
        style_chart(fig, "Risk Matrix")
        st.plotly_chart(fig, use_container_width=True)

    c4, c5 = st.columns(2)

    with c4:
        top_rfi = (df.groupby("Contractor")["RFIs Open"].sum()
                     .reset_index().sort_values("RFIs Open", ascending=False)
                     .head(10).sort_values("RFIs Open"))
        fig = go.Figure(go.Bar(
            y=top_rfi["Contractor"], x=top_rfi["RFIs Open"],
            orientation="h", marker_color=COLORS["primary"],
            text=top_rfi["RFIs Open"], textposition="outside",
        ))
        style_chart(fig, "Open RFIs by Contractor (Top 10)")
        st.plotly_chart(fig, use_container_width=True)

    with c5:
        co_pt = (df.groupby(["Project Type", "Budget Status"])["Change Orders"]
                   .sum().reset_index())
        fig = px.bar(
            co_pt, x="Project Type", y="Change Orders", color="Budget Status",
            color_discrete_map={"Within Budget": COLORS["success"], "Over Budget": COLORS["danger"]},
            barmode="group",
        )
        style_chart(fig, "Change Orders by Project Type")
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE 5: MONTHLY TREND
# ─────────────────────────────────────────────
def page_monthly_trend(df):
    monthly = (df.groupby(["Month", "Month_Num"])
                 .agg(Count=("ID", "count"), Budget=("Budget", "sum"),
                      Cost=("Cost", "sum"), Safety=("Safety Incidents", "sum"))
                 .reset_index()
                 .sort_values("Month_Num"))
    monthly["Month"] = pd.Categorical(monthly["Month"], categories=MONTH_ORDER, ordered=True)
    monthly = monthly.sort_values("Month")

    c1, c2 = st.columns([1, 2])

    with c1:
        fig = go.Figure(go.Bar(
            y=monthly["Month"], x=monthly["Count"],
            orientation="h", marker_color=COLORS["primary"],
            text=monthly["Count"], textposition="outside",
        ))
        style_chart(fig, "# of Projects by Month", height=420)
        fig.update_layout(yaxis=dict(showgrid=False, categoryorder="array",
                                     categoryarray=list(reversed(MONTH_ORDER))))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["Month"], y=monthly["Budget"],
            name="Budget", marker_color=COLORS["dark"],
            text=[f"${v/1000:.2f}M" for v in monthly["Budget"]],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.add_trace(go.Bar(
            x=monthly["Month"], y=monthly["Cost"],
            name="Cost", marker_color=COLORS["secondary"],
            text=[f"${v/1000:.2f}M" for v in monthly["Cost"]],
            textposition="outside", textfont=dict(size=9, color="#1B2631"),
        ))
        fig.update_layout(barmode="group")
        style_chart(fig, "Budget and Cost by Month", height=420)
        st.plotly_chart(fig, use_container_width=True)

    # Full width — Safety incidents by month
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["Month"], y=monthly["Safety"],
        mode="lines+markers+text",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=10, color=COLORS["accent"], symbol="circle",
                    line=dict(color=COLORS["primary"], width=2)),
        text=monthly["Safety"], textposition="top center",
        fill="tozeroy",
        fillcolor="rgba(168,218,220,0.2)",
        name="Safety Incidents",
    ))
    style_chart(fig, "Safety Incidents by Month", height=280)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# PAGE 6: DECOMPOSITION VIEW
# ─────────────────────────────────────────────
def page_decomposition(df):
    st.markdown("#### Project Drill-Down Explorer")

    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    search = fc1.text_input("Project Name Search", placeholder="Type to filter...")
    sel_type = fc2.selectbox("Project Type", ["All"] + sorted(df["Project Type"].unique()), key="dc_type")
    sel_dept = fc3.selectbox("Department", ["All"] + sorted(df["Department"].unique()), key="dc_dept")
    sel_phase = fc4.selectbox("Phase", ["All"] + sorted(df["Phase"].unique()), key="dc_phase")
    sel_contr = fc5.selectbox("Contractor", ["All"] + sorted(df["Contractor"].unique()), key="dc_contr")

    ddf = df.copy()
    if search:
        ddf = ddf[ddf["Project Name"].str.contains(search, case=False)]
    if sel_type != "All":
        ddf = ddf[ddf["Project Type"] == sel_type]
    if sel_dept != "All":
        ddf = ddf[ddf["Department"] == sel_dept]
    if sel_phase != "All":
        ddf = ddf[ddf["Phase"] == sel_phase]
    if sel_contr != "All":
        ddf = ddf[ddf["Contractor"] == sel_contr]

    st.markdown(f"**{len(ddf)} projects** match your filters")

    # Treemap decomposition
    treemap_data = (ddf.groupby(["Project Type", "Department", "Phase"])
                      .size().reset_index(name="Count"))
    if not treemap_data.empty:
        fig = px.treemap(
            treemap_data,
            path=["Project Type", "Department", "Phase"],
            values="Count",
            color="Count",
            color_continuous_scale=[[0, COLORS["secondary"]], [1, COLORS["dark"]]],
        )
        fig.update_traces(textinfo="label+value")
        style_chart(fig, "Project Decomposition: Type → Department → Phase", height=400)
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Sankey: Region → Project Type → Status
    st.markdown("#### Portfolio Flow: Region → Project Type → Status")
    regions = sorted(ddf["Region"].unique())
    types = sorted(ddf["Project Type"].unique())
    statuses = sorted(ddf["Status"].unique())

    all_nodes = regions + types + statuses
    node_idx = {n: i for i, n in enumerate(all_nodes)}

    sources, targets, values = [], [], []
    for _, row in (ddf.groupby(["Region", "Project Type"]).size().reset_index(name="n")).iterrows():
        sources.append(node_idx[row["Region"]])
        targets.append(node_idx[row["Project Type"]])
        values.append(row["n"])
    for _, row in (ddf.groupby(["Project Type", "Status"]).size().reset_index(name="n")).iterrows():
        sources.append(node_idx[row["Project Type"]])
        targets.append(node_idx[row["Status"]])
        values.append(row["n"])

    node_colors = (
        [COLORS["dark"]] * len(regions) +
        [COLORS["primary"]] * len(types) +
        [STATUS_COLORS.get(s, COLORS["muted"]) for s in statuses]
    )

    fig = go.Figure(go.Sankey(
        node=dict(label=all_nodes, color=node_colors, pad=15, thickness=20),
        link=dict(source=sources, target=targets, value=values,
                  color="rgba(46,134,171,0.2)"),
    ))
    style_chart(fig, "", height=420)
    fig.update_layout(title=dict(text=""))
    st.plotly_chart(fig, use_container_width=True)

    # Project detail card
    if search and len(ddf) == 1:
        proj = ddf.iloc[0]
        st.markdown("#### Selected Project Detail")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Budget", f"${proj['Budget']:,.1f}K")
        d2.metric("Cost", f"${proj['Cost']:,.1f}K",
                  delta=f"{'Over' if proj['Cost'] > proj['Budget'] else 'Under'} budget")
        d3.metric("Schedule Variance", f"{proj['Schedule Variance (%)']:+.1f}%")
        d4.metric("Safety Incidents", int(proj["Safety Incidents"]))


# ─────────────────────────────────────────────
# PAGE 7: AI ASSISTANT
# ─────────────────────────────────────────────
def page_ai_assistant(df):
    st.markdown("### 🤖 AI Portfolio Assistant")
    st.markdown("Ask anything about your project portfolio — powered by Claude AI.")

    # Build context
    n = len(df)
    total_budget = df["Budget"].sum()
    total_cost = df["Cost"].sum()
    over_budget_count = (df["Budget Status"] == "Over Budget").sum()
    over_budget_pct = over_budget_count / n * 100 if n else 0
    total_incidents = int(df["Safety Incidents"].sum())

    over_budget_df = (df[df["Budget Status"] == "Over Budget"]
                        .sort_values("Cost", ascending=False)
                        .head(5)[["Project Name", "Region", "Contractor", "Budget", "Cost"]])
    sched_risk_df = (df.sort_values("Schedule Variance (%)", ascending=False)
                       .head(5)[["Project Name", "Region", "Contractor", "Schedule Variance (%)"]])
    region_summary = df.groupby("Region").agg(
        Projects=("ID", "count"),
        Budget=("Budget", "sum"),
        Cost=("Cost", "sum"),
        Incidents=("Safety Incidents", "sum"),
    ).to_string()

    system_prompt = f"""You are an expert construction project intelligence analyst for Summit Line Construction,
an electrical infrastructure company. You help project managers and executives understand their portfolio data.

CURRENT PORTFOLIO SUMMARY (filtered data):
- Total Projects: {n}
- Total Budget: ${total_budget/1000:,.1f}K
- Total Cost: ${total_cost/1000:,.1f}K
- Over Budget Projects: {over_budget_count} ({over_budget_pct:.1f}%)
- Total Safety Incidents: {total_incidents}

TOP 5 OVER-BUDGET PROJECTS:
{over_budget_df.to_string(index=False)}

TOP 5 SCHEDULE RISK PROJECTS:
{sched_risk_df.to_string(index=False)}

REGIONAL BREAKDOWN:
{region_summary}

Provide concise, actionable insights. Use bullet points and formatting for clarity.
Focus on construction project management best practices and risk mitigation."""

    # Suggested questions
    suggested = [
        "Which region has the highest budget overrun?",
        "What is our biggest safety risk this month?",
        "Which contractor is performing best?",
        "Where should leadership focus this week?",
        "Which projects are at risk of missing closeout?",
    ]

    st.markdown("**Suggested questions:**")
    q_cols = st.columns(len(suggested))
    for i, q in enumerate(suggested):
        if q_cols[i].button(q, key=f"suggest_{i}", use_container_width=True):
            if "messages" not in st.session_state:
                st.session_state.messages = []
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

    # Initialize chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your project portfolio..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # Generate response for last unanswered user message
    if (st.session_state.messages and
            st.session_state.messages[-1]["role"] == "user"):

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                client = Mistral(api_key=st.secrets["MISTRAL_API_KEY"])
                mistral_messages = [{"role": "system", "content": system_prompt}] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                with client.chat.stream(
                    model="mistral-large-latest",
                    messages=mistral_messages,
                ) as stream:
                    for chunk in stream:
                        delta = chunk.data.choices[0].delta.content or ""
                        full_response += delta
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"⚠️ Error connecting to Mistral API: {str(e)}"
                response_placeholder.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    selected = render_sidebar()

    # Global filter bar
    with st.container():
        filters = render_filters(df_raw)

    df = apply_filters(df_raw, filters)

    if df.empty:
        st.warning("No projects match the selected filters. Please adjust your filters.")
        return

    if selected == "📊 Overview":
        page_overview(df)
    elif selected == "💰 Budget vs Cost":
        page_budget_vs_cost(df)
    elif selected == "🏗️ Contractor & Department":
        page_contractor_dept(df)
    elif selected == "🦺 Safety & Risk":
        page_safety_risk(df)
    elif selected == "📅 Monthly Trend":
        page_monthly_trend(df)
    elif selected == "🔍 Decomposition View":
        page_decomposition(df)
    elif selected == "🤖 AI Assistant":
        page_ai_assistant(df)


if __name__ == "__main__":
    main()
