# dashboard.py — Summit Line Construction Dashboard (Plotly Dash)
import os
import json
import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data import df_raw, MONTH_ORDER

# ── API key ───────────────────────────────────────────────────────────────────
MISTRAL_KEY = ""
try:
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as _f:
        _sec = tomllib.load(_f)
    MISTRAL_KEY = _sec.get("MISTRAL_API_KEY", "")
except Exception:
    MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")

# ── Palette ───────────────────────────────────────────────────────────────────
P    = "#2E86AB"
DARK = "#1B4965"
SEC  = "#A8DADC"
ACC  = "#F4A261"
RED  = "#E63946"
GRN  = "#2DC653"
YLW  = "#FFB703"
TXT  = "#111111"
MUT  = "#666666"
SBG  = "#1B2631"
STATUS_C = {"Planning": P, "In Progress": YLW, "On Hold": RED, "Completed": GRN}

# ── Figure styling ────────────────────────────────────────────────────────────
def sf(fig, title="", height=300):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=TXT, family="Arial"), x=0),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial", size=11, color=TXT),
        margin=dict(l=8, r=8, t=44 if title else 10, b=8),
        legend=dict(font=dict(color=TXT, size=11), bgcolor="white", borderwidth=0),
        xaxis=dict(showgrid=True, gridcolor="#E8E8E8", zeroline=False,
                   tickfont=dict(color=TXT), title_font=dict(color=TXT)),
        yaxis=dict(showgrid=True, gridcolor="#E8E8E8", zeroline=False,
                   tickfont=dict(color=TXT), title_font=dict(color=TXT)),
        height=height,
        hoverlabel=dict(bgcolor="white", font_color=TXT, bordercolor="#CCC"),
    )
    return fig

# ── Layout helpers ────────────────────────────────────────────────────────────
def G(fig):
    return dcc.Graph(figure=fig, config={"displayModeBar": False},
                     style={"width": "100%"})

def CC(content, extra=None):
    s = {"background": "white", "borderRadius": "8px", "padding": "12px",
         "boxShadow": "0 1px 4px rgba(0,0,0,0.08)", "marginBottom": "0"}
    if extra:
        s.update(extra)
    kids = content if isinstance(content, list) else [content]
    return html.Div(kids, style=s)

def Row(*items):
    return html.Div(list(items),
                    style={"display": "flex", "gap": "12px",
                           "marginBottom": "12px", "alignItems": "stretch"})

def Col(content, flex=1):
    kids = content if isinstance(content, list) else [content]
    return html.Div(kids, style={"flex": str(flex), "minWidth": "0"})

def KRow(items):
    cards = [html.Div([
        html.Div(str(v), style={"fontSize": "1.85rem", "fontWeight": "800",
                                 "color": DARK, "lineHeight": "1.1"}),
        html.Div(l, style={"fontSize": "11px", "color": c,
                           "fontWeight": "700", "marginTop": "5px"}),
    ], style={
        "background": "white", "borderRadius": "8px", "padding": "18px",
        "textAlign": "center", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
        "borderTop": f"4px solid {c}", "flex": "1", "minWidth": "0",
    }) for l, v, c in items]
    return html.Div(cards, style={"display": "flex", "gap": "12px", "marginBottom": "12px"})

# ── Filters ───────────────────────────────────────────────────────────────────
FILTER_FIELDS = ["Region", "Status", "Project Type", "Phase",
                 "Department", "Contractor", "Budget Status"]
FILTER_IDS    = [f"f-{f.lower().replace(' ','-')}" for f in FILTER_FIELDS]

def apply_filters(df, *vals):
    out = df.copy()
    for field, val in zip(FILTER_FIELDS, vals):
        if val and val != "All":
            out = out[out[field] == val]
    return out

# ── Pages ─────────────────────────────────────────────────────────────────────

def page_overview(df):
    n   = len(df)
    tb  = df["Budget"].sum() / 1000
    tc  = df["Cost"].sum() / 1000
    cpp = df["Cost"].mean() / 1000 if n else 0
    inc = int(df["Safety Incidents"].sum())

    reg = df.groupby("Region").size().reset_index(name="n").sort_values("n")
    f1 = go.Figure(go.Bar(x=reg["n"], y=reg["Region"], orientation="h",
                          marker_color=P, text=reg["n"], textposition="outside",
                          textfont=dict(color=TXT, size=11)))
    sf(f1, "# of Projects by Region"); f1.update_layout(yaxis_showgrid=False)

    stat = df.groupby("Status").size().reset_index(name="n")
    f2 = go.Figure(go.Pie(
        labels=stat["Status"], values=stat["n"], hole=0.42,
        marker=dict(colors=[STATUS_C.get(s, MUT) for s in stat["Status"]]),
        textinfo="label+percent",
        textfont=dict(color=TXT, size=10),
        insidetextfont=dict(color=TXT),
    ))
    sf(f2, "# of Projects by Status")
    f2.update_layout(legend=dict(orientation="v", x=1.02, y=0.5))

    PO = ["Foundation", "Finishing", "Design", "Structure", "Closeout"]
    ph = df.groupby("Phase").size().reset_index(name="n")
    ph["Phase"] = pd.Categorical(ph["Phase"], categories=PO, ordered=True)
    ph = ph.sort_values("Phase")
    f3 = go.Figure(go.Bar(x=ph["Phase"], y=ph["n"], marker_color=P,
                          text=ph["n"], textposition="outside", textfont=dict(color=TXT, size=11)))
    sf(f3, "# of Projects by Phase")

    mo = (df.groupby(["Month", "Month_Num"]).size().reset_index(name="n")
            .sort_values("Month_Num"))
    mo["Month"] = pd.Categorical(mo["Month"], categories=MONTH_ORDER, ordered=True)
    mo = mo.sort_values("Month")
    f4 = go.Figure()
    f4.add_trace(go.Bar(x=mo["Month"], y=mo["n"], marker_color=SEC, name="Projects"))
    f4.add_trace(go.Scatter(x=mo["Month"], y=mo["n"], mode="lines+markers+text",
                            line=dict(color=DARK, width=2),
                            marker=dict(size=8, color=ACC, line=dict(color=DARK, width=1)),
                            text=mo["n"], textposition="top center",
                            textfont=dict(color=TXT, size=10), name="Trend"))
    sf(f4, "# of Projects by Month")

    cp = df.groupby("Project Type")["Cost"].mean().reset_index()
    cp.columns = ["Type", "AvgCost"]
    cp = cp.sort_values("AvgCost", ascending=False)
    f5 = go.Figure(go.Bar(x=cp["Type"], y=cp["AvgCost"], marker_color=P,
                          text=[f"${v/1000:.1f}K" for v in cp["AvgCost"]],
                          textposition="outside", textfont=dict(color=TXT, size=11)))
    sf(f5, "Cost Per Project by Project Type")

    return html.Div([
        KRow([("# of Projects", f"{n:,}", P), ("Total Budget", f"${tb:,.1f}K", DARK),
              ("Total Cost", f"${tc:,.1f}K", P), ("Cost Per Project", f"${cpp:,.1f}K", ACC),
              ("Safety Incidents", f"{inc:,}", RED)]),
        Row(Col(CC(G(f1))), Col(CC(G(f2))), Col(CC(G(f3)))),
        Row(Col(CC(G(f4)), flex=2), Col(CC(G(f5)), flex=1)),
    ])


def page_budget(df):
    def gb(col, orient="v", h=300):
        g = df.groupby(col).agg(Budget=("Budget", "sum"), Cost=("Cost", "sum")).reset_index()
        g = g.sort_values("Budget", ascending=(orient == "h"))
        fig = go.Figure()
        if orient == "h":
            fig.add_trace(go.Bar(y=g[col], x=g["Budget"], orientation="h", name="Budget",
                                 marker_color=DARK,
                                 text=[f"${v/1000:.1f}K" for v in g["Budget"]],
                                 textposition="outside", textfont=dict(color=TXT, size=10)))
            fig.add_trace(go.Bar(y=g[col], x=g["Cost"], orientation="h", name="Cost",
                                 marker_color=SEC,
                                 text=[f"${v/1000:.1f}K" for v in g["Cost"]],
                                 textposition="outside", textfont=dict(color=TXT, size=10)))
        else:
            fig.add_trace(go.Bar(x=g[col], y=g["Budget"], name="Budget", marker_color=DARK,
                                 text=[f"${v/1000:.1f}K" for v in g["Budget"]],
                                 textposition="outside", textfont=dict(color=TXT, size=10)))
            fig.add_trace(go.Bar(x=g[col], y=g["Cost"], name="Cost", marker_color=SEC,
                                 text=[f"${v/1000:.1f}K" for v in g["Cost"]],
                                 textposition="outside", textfont=dict(color=TXT, size=10)))
        fig.update_layout(barmode="group")
        sf(fig, f"Budget and Cost by {col}", h)
        return fig

    f1 = gb("Department", "h")
    f2 = gb("Project Type", "v")
    f3 = gb("Region", "h")

    t7 = (df.groupby("Contractor").agg(Budget=("Budget","sum"), Cost=("Cost","sum"))
            .reset_index().sort_values("Budget", ascending=False).head(7))
    fc = go.Figure()
    fc.add_trace(go.Bar(x=t7["Contractor"], y=t7["Budget"], name="Budget", marker_color=DARK,
                        text=[f"${v/1000:.0f}K" for v in t7["Budget"]],
                        textposition="outside", textfont=dict(color=TXT, size=10)))
    fc.add_trace(go.Bar(x=t7["Contractor"], y=t7["Cost"], name="Cost", marker_color=SEC,
                        text=[f"${v/1000:.0f}K" for v in t7["Cost"]],
                        textposition="outside", textfont=dict(color=TXT, size=10)))
    fc.add_trace(go.Scatter(x=t7["Contractor"], y=t7["Cost"], mode="lines+markers",
                            line=dict(color=ACC, width=2),
                            marker=dict(size=8, color=ACC), name="Cost Trend"))
    fc.update_layout(barmode="group")
    sf(fc, "Budget and Cost by Top 7 Contractors", 340)

    return html.Div([
        Row(Col(CC(G(f1))), Col(CC(G(f2))), Col(CC(G(f3)))),
        CC(G(fc)),
    ])


def page_contractor(df):
    t7 = (df.groupby("Contractor").size().reset_index(name="n")
            .sort_values("n", ascending=False).head(7).sort_values("n"))
    f1 = go.Figure(go.Bar(x=t7["n"], y=t7["Contractor"], orientation="h",
                          marker_color=P, text=t7["n"], textposition="outside",
                          textfont=dict(color=TXT)))
    sf(f1, "# of Projects by Top 7 Contractor"); f1.update_layout(yaxis_showgrid=False)

    dept = df.groupby("Department").size().reset_index(name="n")
    f2 = px.treemap(dept, path=["Department"], values="n",
                    color="n", color_continuous_scale=[[0, SEC], [1, DARK]])
    f2.update_traces(textfont=dict(size=14, color="white"))
    sf(f2, "# of Projects by Department"); f2.update_layout(coloraxis_showscale=False)

    si = (df.groupby("Contractor")["Safety Incidents"].sum().reset_index()
            .sort_values("Safety Incidents", ascending=False).head(7))
    f3 = go.Figure(go.Bar(x=si["Contractor"], y=si["Safety Incidents"],
                          marker_color=TXT, text=si["Safety Incidents"],
                          textposition="outside", textfont=dict(color=TXT)))
    sf(f3, "Safety Incidents by Top 7 Contractor")
    f3.update_layout(xaxis=dict(tickangle=-30))

    # Data table
    tdf = df[["ID","Project Name","Project Type","Region","Status",
              "Contractor","Department","Budget","Cost"]].copy()
    header = html.Tr([
        html.Th(c, style={"background": DARK, "color": "white", "padding": "8px 10px",
                          "fontSize": "11px", "fontWeight": "700", "whiteSpace": "nowrap",
                          "position": "sticky", "top": "0"})
        for c in ["ID","Project Name","Type","Region","Status","Contractor","Dept","Budget","Cost"]
    ])
    rows = []
    for _, r in tdf.iterrows():
        cc = RED if r["Cost"] > r["Budget"] else GRN
        rows.append(html.Tr([
            html.Td(r["ID"],           style={"padding":"5px 10px","fontSize":"11px","color":TXT}),
            html.Td(r["Project Name"], style={"padding":"5px 10px","fontSize":"11px","color":TXT,"whiteSpace":"nowrap"}),
            html.Td(r["Project Type"], style={"padding":"5px 10px","fontSize":"11px","color":TXT}),
            html.Td(r["Region"],       style={"padding":"5px 10px","fontSize":"11px","color":TXT}),
            html.Td(r["Status"],       style={"padding":"5px 10px","fontSize":"11px","color":TXT}),
            html.Td(r["Contractor"],   style={"padding":"5px 10px","fontSize":"11px","color":TXT,"whiteSpace":"nowrap"}),
            html.Td(r["Department"],   style={"padding":"5px 10px","fontSize":"11px","color":TXT}),
            html.Td(f"${r['Budget']:,.1f}", style={"padding":"5px 10px","fontSize":"11px","color":TXT,"textAlign":"right"}),
            html.Td(f"${r['Cost']:,.1f}",   style={"padding":"5px 10px","fontSize":"11px","color":cc,"fontWeight":"700","textAlign":"right"}),
        ], style={"borderBottom": "1px solid #F0F0F0", "background": "white"}))

    table = html.Div([
        html.Div("Project Detail", style={"fontWeight":"700","fontSize":"13px","color":TXT,"marginBottom":"8px"}),
        html.Div(
            html.Table([html.Thead(header), html.Tbody(rows)],
                       style={"width":"100%","borderCollapse":"collapse"}),
            style={"overflowY":"auto","maxHeight":"320px","border":"1px solid #EEE","borderRadius":"6px"}
        )
    ])

    return html.Div([
        Row(Col(CC(G(f1))), Col(CC(G(f2))), Col(CC(G(f3)))),
        CC(table),
    ])


def page_safety(df):
    n   = len(df)
    inc = int(df["Safety Incidents"].sum())
    ob  = (df["Budget Status"] == "Over Budget").sum()
    sv  = df["Schedule Variance (%)"].mean()
    rf  = int(df["RFIs Open"].sum())
    co  = int(df["Change Orders"].sum())

    rsi = (df.groupby("Region")["Safety Incidents"].sum()
             .reset_index().sort_values("Safety Incidents"))
    f1 = go.Figure(go.Bar(x=rsi["Safety Incidents"], y=rsi["Region"], orientation="h",
                          marker_color=RED, text=rsi["Safety Incidents"],
                          textposition="outside", textfont=dict(color=TXT)))
    sf(f1, "Safety Incidents by Region"); f1.update_layout(yaxis_showgrid=False)

    bs = df["Budget Status"].value_counts().reset_index()
    bs.columns = ["Status","Count"]
    f2 = go.Figure(go.Pie(labels=bs["Status"], values=bs["Count"], hole=0.4,
                          marker=dict(colors=[GRN, RED]),
                          textfont=dict(color=TXT), insidetextfont=dict(color=TXT)))
    sf(f2, "Budget Status Distribution")

    dfc = df.copy()
    dfc["Burn%"] = (dfc["Cost"] / dfc["Budget"] * 100).clip(0, 150)
    dfc["Risk"] = dfc.apply(
        lambda r: "Critical" if r["Burn%"] > 110 and r["Schedule Variance (%)"] > 10
        else "High"   if r["Burn%"] > 100 or r["Schedule Variance (%)"] > 10
        else "Medium" if r["Burn%"] > 90 else "Low", axis=1)
    f3 = px.scatter(dfc, x="Schedule Variance (%)", y="Burn%", size="Crew Size",
                    color="Risk",
                    color_discrete_map={"Critical":RED,"High":ACC,"Medium":YLW,"Low":GRN},
                    hover_name="Project Name", opacity=0.7)
    sf(f3, "Risk Matrix")

    trfi = (df.groupby("Contractor")["RFIs Open"].sum().reset_index()
              .sort_values("RFIs Open", ascending=False).head(10).sort_values("RFIs Open"))
    f4 = go.Figure(go.Bar(y=trfi["Contractor"], x=trfi["RFIs Open"], orientation="h",
                          marker_color=P, text=trfi["RFIs Open"],
                          textposition="outside", textfont=dict(color=TXT)))
    sf(f4, "Open RFIs by Contractor (Top 10)"); f4.update_layout(yaxis_showgrid=False)

    cot = df.groupby(["Project Type","Budget Status"])["Change Orders"].sum().reset_index()
    f5 = px.bar(cot, x="Project Type", y="Change Orders", color="Budget Status",
                color_discrete_map={"Within Budget": GRN, "Over Budget": RED},
                barmode="group", text_auto=True)
    f5.update_traces(textfont=dict(color=TXT))
    sf(f5, "Change Orders by Project Type")

    return html.Div([
        KRow([("Safety Incidents", f"{inc:,}", RED),
              ("Over Budget", f"{ob} ({ob/n*100:.0f}%)" if n else "0", ACC),
              ("Avg Schedule Var.", f"{sv:+.1f}%", YLW),
              ("Total Open RFIs", f"{rf:,}", P),
              ("Total Change Orders", f"{co:,}", DARK)]),
        Row(Col(CC(G(f1))), Col(CC(G(f2))), Col(CC(G(f3)))),
        Row(Col(CC(G(f4))), Col(CC(G(f5)))),
    ])


def page_monthly(df):
    mo = (df.groupby(["Month","Month_Num"])
            .agg(Count=("ID","count"), Budget=("Budget","sum"),
                 Cost=("Cost","sum"), Safety=("Safety Incidents","sum"))
            .reset_index().sort_values("Month_Num"))
    mo["Month"] = pd.Categorical(mo["Month"], categories=MONTH_ORDER, ordered=True)
    mo = mo.sort_values("Month")

    f1 = go.Figure(go.Bar(y=mo["Month"], x=mo["Count"], orientation="h",
                          marker_color=P, text=mo["Count"], textposition="outside",
                          textfont=dict(color=TXT)))
    sf(f1, "# of Projects by Month", 420)
    f1.update_layout(yaxis=dict(showgrid=False, categoryorder="array",
                                categoryarray=list(reversed(MONTH_ORDER))))

    f2 = go.Figure()
    f2.add_trace(go.Bar(x=mo["Month"], y=mo["Budget"], name="Budget", marker_color=DARK,
                        text=[f"${v/1000:.2f}M" for v in mo["Budget"]],
                        textposition="outside", textfont=dict(color=TXT, size=9)))
    f2.add_trace(go.Bar(x=mo["Month"], y=mo["Cost"], name="Cost", marker_color=SEC,
                        text=[f"${v/1000:.2f}M" for v in mo["Cost"]],
                        textposition="outside", textfont=dict(color=TXT, size=9)))
    f2.update_layout(barmode="group")
    sf(f2, "Budget and Cost by Month", 420)

    f3 = go.Figure(go.Scatter(
        x=mo["Month"], y=mo["Safety"], mode="lines+markers+text",
        line=dict(color=P, width=2),
        marker=dict(size=10, color=ACC, line=dict(color=P, width=2)),
        text=mo["Safety"], textposition="top center",
        textfont=dict(color=TXT, size=10),
        fill="tozeroy", fillcolor="rgba(168,218,220,0.12)", name="Incidents",
    ))
    sf(f3, "Safety Incidents by Month", 260)

    return html.Div([
        Row(Col(CC(G(f1))), Col(CC(G(f2)), flex=2)),
        CC(G(f3)),
    ])


def page_decomp(df):
    td = df.groupby(["Project Type","Department","Phase"]).size().reset_index(name="n")
    if not td.empty:
        f1 = px.treemap(td, path=["Project Type","Department","Phase"], values="n",
                        color="n", color_continuous_scale=[[0,SEC],[1,DARK]])
        f1.update_traces(textfont=dict(color="white", size=12))
        f1.update_layout(coloraxis_showscale=False)
    else:
        f1 = go.Figure()
    sf(f1, "Project Decomposition: Type → Department → Phase", 380)

    regions  = sorted(df["Region"].unique())
    types    = sorted(df["Project Type"].unique())
    statuses = sorted(df["Status"].unique())
    all_nodes = regions + types + statuses
    idx = {n: i for i, n in enumerate(all_nodes)}
    srcs, tgts, vals = [], [], []
    for _, r in df.groupby(["Region","Project Type"]).size().reset_index(name="n").iterrows():
        srcs.append(idx[r["Region"]]); tgts.append(idx[r["Project Type"]]); vals.append(r["n"])
    for _, r in df.groupby(["Project Type","Status"]).size().reset_index(name="n").iterrows():
        srcs.append(idx[r["Project Type"]]); tgts.append(idx[r["Status"]]); vals.append(r["n"])
    nc = [DARK]*len(regions) + [P]*len(types) + [STATUS_C.get(s, MUT) for s in statuses]
    f2 = go.Figure(go.Sankey(
        node=dict(label=all_nodes, color=nc, pad=15, thickness=20,
                  line=dict(color="#888", width=0.5)),
        link=dict(source=srcs, target=tgts, value=vals, color="rgba(46,134,171,0.12)"),
    ))
    sf(f2, "Portfolio Flow: Region → Project Type → Status", 400)

    return html.Div([CC(G(f1)), CC(G(f2))])


def page_ai(df):
    n   = len(df); tb = df["Budget"].sum(); tc = df["Cost"].sum()
    ob  = (df["Budget Status"] == "Over Budget").sum()
    inc = int(df["Safety Incidents"].sum())
    top_ob = (df[df["Budget Status"]=="Over Budget"]
                .sort_values("Cost", ascending=False).head(5)
                [["Project Name","Region","Contractor","Budget","Cost"]]
                .to_string(index=False))
    top_sr = (df.sort_values("Schedule Variance (%)", ascending=False).head(5)
                [["Project Name","Region","Contractor","Schedule Variance (%)"]]
                .to_string(index=False))
    reg_sum = df.groupby("Region").agg(
        Projects=("ID","count"), Budget=("Budget","sum"),
        Cost=("Cost","sum"), Incidents=("Safety Incidents","sum")).to_string()

    sys_ctx = json.dumps({
        "n": int(n), "tb": float(tb), "tc": float(tc), "ob": int(ob), "inc": int(inc),
        "top_ob": top_ob, "top_sr": top_sr, "reg": reg_sum,
    })

    SUGGESTIONS = [
        "Which region has the highest budget overrun?",
        "What is our biggest safety risk?",
        "Which contractor is performing best?",
        "Where should leadership focus this week?",
        "Which projects are at risk of missing closeout?",
    ]

    return html.Div([
        dcc.Store(id="chat-store", data=[]),
        dcc.Store(id="sys-ctx", data=sys_ctx),

        html.H5("🤖 AI Portfolio Assistant",
                style={"color": TXT, "fontWeight": "800", "marginBottom": "4px"}),
        html.P("Ask anything about your project portfolio.",
               style={"color": MUT, "fontSize": "13px", "marginBottom": "16px"}),

        # Suggest chips
        html.Div([
            html.Div("Suggested:", style={"fontSize":"11px","fontWeight":"700",
                                          "color":MUT,"marginBottom":"8px"}),
            html.Div([
                html.Button(q, id=f"suggest-{i}",
                            style={"background":"white","border":f"1px solid {P}",
                                   "borderRadius":"20px","padding":"6px 14px",
                                   "fontSize":"12px","color":P,"cursor":"pointer",
                                   "marginRight":"8px","marginBottom":"8px"})
                for i, q in enumerate(SUGGESTIONS)
            ]),
        ], style={"marginBottom": "16px"}),

        # Chat display
        html.Div(id="chat-display",
                 style={"height":"380px","overflowY":"auto","background":"#FAFAFA",
                        "borderRadius":"8px","padding":"12px","marginBottom":"12px",
                        "border":"1px solid #EEE"}),

        # Input row
        html.Div([
            dcc.Input(id="chat-input", type="text", debounce=False,
                      placeholder="Ask about your portfolio...",
                      style={"flex":"1","padding":"10px 14px","fontSize":"13px",
                             "border":"1px solid #DDD","borderRadius":"6px",
                             "color":TXT,"outline":"none","background":"white"}),
            html.Button("Send", id="chat-send",
                        style={"marginLeft":"8px","background":P,"color":"white",
                               "border":"none","borderRadius":"6px",
                               "padding":"10px 22px","fontSize":"13px",
                               "cursor":"pointer","fontWeight":"700"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"background":"white","borderRadius":"8px","padding":"24px",
              "boxShadow":"0 1px 4px rgba(0,0,0,0.08)"})


# ── App layout ────────────────────────────────────────────────────────────────
NAV = [
    ("/",            "📊", "Overview"),
    ("/budget",      "💰", "Budget vs Cost"),
    ("/contractor",  "🏗️", "Contractor & Dept"),
    ("/safety",      "🦺", "Safety & Risk"),
    ("/monthly",     "📅", "Monthly Trend"),
    ("/decomp",      "🔍", "Decomposition"),
    ("/ai",          "🤖", "AI Assistant"),
]

sidebar = html.Div([
    html.Div([
        html.Img(src="/assets/logo.png",
                 style={"width":"130px","height":"130px","borderRadius":"50%",
                        "display":"block","margin":"0 auto 8px auto",
                        "border":"2px solid rgba(255,255,255,0.15)"}),
        html.Div("Project Intelligence Platform",
                 style={"color":SEC,"fontSize":"10px","marginTop":"4px","textAlign":"center"}),
    ], style={"background":DARK,"padding":"16px 12px","borderRadius":"8px",
              "textAlign":"center","marginBottom":"20px"}),

    html.Div(id="nav-links", children=[
        dcc.Link(
            html.Div([
                html.Span(icon, style={"marginRight":"10px","fontSize":"14px"}),
                html.Span(label, style={"fontSize":"13px","fontWeight":"500"}),
            ], style={"display":"flex","alignItems":"center"}),
            href=href,
            style={"display":"block","padding":"10px 14px","color":"rgba(255,255,255,0.85)",
                   "textDecoration":"none","borderRadius":"6px","marginBottom":"3px",
                   "transition":"background 0.15s"},
        ) for href, icon, label in NAV
    ]),

    html.Hr(style={"borderColor":"rgba(255,255,255,0.12)","margin":"20px 0"}),
    html.Div("Summit Line Construction",
             style={"color":"#555","fontSize":"10px","textAlign":"center"}),
], style={
    "position":"fixed","top":0,"left":0,"bottom":0,"width":"220px",
    "background":SBG,"padding":"16px 12px","overflowY":"auto",
    "zIndex":1000,"boxShadow":"2px 0 8px rgba(0,0,0,0.12)",
})

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Summit Line Construction",
)
server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    sidebar,

    html.Div([
        # Header logo
        html.Div([
            html.Img(src="/assets/header_logo.png",
                     style={"height":"80px","display":"block","margin":"0 auto"}),
        ], style={"marginBottom":"14px","paddingBottom":"12px",
                  "borderBottom":"1px solid #EEEEEE","textAlign":"center"}),

        # Filter bar
        html.Div([
            html.Div([
                html.Div([
                    html.Label(f.upper(),
                               style={"fontSize":"9px","fontWeight":"700",
                                      "color":MUT,"marginBottom":"2px","display":"block"}),
                    dcc.Dropdown(
                        id=fid,
                        options=[{"label":"All","value":"All"}] +
                                [{"label":v,"value":v}
                                 for v in sorted(df_raw[f].dropna().unique())],
                        value="All", clearable=False,
                        style={"fontSize":"12px","color":TXT},
                    ),
                ], style={"flex":"1","minWidth":"0"})
                for f, fid in zip(FILTER_FIELDS, FILTER_IDS)
            ], style={"display":"flex","gap":"8px","alignItems":"flex-end"}),
        ], style={"background":"white","padding":"10px 14px","borderRadius":"8px",
                  "boxShadow":"0 1px 3px rgba(0,0,0,0.08)","marginBottom":"14px",
                  "border":"1px solid #F0F0F0"}),

        html.Div(id="page-content"),
    ], style={
        "marginLeft":"236px","padding":"16px 20px",
        "background":"white","minHeight":"100vh",
        "fontFamily":"Arial, sans-serif",
    }),
], style={"background":"white","fontFamily":"Arial, sans-serif"})


# ── Main page callback ────────────────────────────────────────────────────────
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")] + [Input(fid, "value") for fid in FILTER_IDS],
)
def render_page(pathname, *fvals):
    df = apply_filters(df_raw, *fvals)
    if df.empty:
        return html.Div("No projects match these filters.",
                        style={"color":MUT,"padding":"60px","textAlign":"center","fontSize":"16px"})
    p = pathname or "/"
    if p == "/":             return page_overview(df)
    if p == "/budget":       return page_budget(df)
    if p == "/contractor":   return page_contractor(df)
    if p == "/safety":       return page_safety(df)
    if p == "/monthly":      return page_monthly(df)
    if p == "/decomp":       return page_decomp(df)
    if p == "/ai":           return page_ai(df)
    return page_overview(df)


# ── Chat callback ─────────────────────────────────────────────────────────────
SUGGESTIONS_TEXT = [
    "Which region has the highest budget overrun?",
    "What is our biggest safety risk?",
    "Which contractor is performing best?",
    "Where should leadership focus this week?",
    "Which projects are at risk of missing closeout?",
]

@app.callback(
    [Output("chat-display", "children"),
     Output("chat-store", "data"),
     Output("chat-input", "value")],
    [Input("chat-send", "n_clicks"),
     Input("chat-input", "n_submit")] +
    [Input(f"suggest-{i}", "n_clicks") for i in range(5)],
    [State("chat-input", "value"),
     State("chat-store", "data"),
     State("sys-ctx", "data")],
    prevent_initial_call=True,
)
def handle_chat(n_send, n_submit, *args):
    suggest_clicks = args[:5]
    user_input, history, sys_ctx_json = args[5], args[6], args[7]

    triggered = ctx.triggered_id
    if triggered and str(triggered).startswith("suggest-"):
        idx = int(str(triggered).split("-")[1])
        user_input = SUGGESTIONS_TEXT[idx]

    if not user_input or not user_input.strip():
        return dash.no_update, dash.no_update, dash.no_update

    history = history or []
    history.append({"role": "user", "content": user_input.strip()})

    # Build Mistral messages
    try:
        ctx_data = json.loads(sys_ctx_json)
        system_prompt = f"""You are an expert construction project analyst for Summit Line Construction.

PORTFOLIO SUMMARY:
- Projects: {ctx_data['n']}
- Total Budget: ${ctx_data['tb']/1000:,.1f}K
- Total Cost: ${ctx_data['tc']/1000:,.1f}K
- Over Budget: {ctx_data['ob']}
- Safety Incidents: {ctx_data['inc']}

TOP OVER-BUDGET PROJECTS:
{ctx_data['top_ob']}

TOP SCHEDULE RISK PROJECTS:
{ctx_data['top_sr']}

REGIONAL BREAKDOWN:
{ctx_data['reg']}

Give concise, actionable insights. Use bullet points for clarity."""
    except Exception:
        system_prompt = "You are a construction project analyst for Summit Line Construction."

    assistant_reply = ""
    try:
        from mistralai.client import Mistral
        client = Mistral(api_key=MISTRAL_KEY)
        msgs = [{"role": "system", "content": system_prompt}] + history
        resp = client.chat.complete(model="mistral-large-latest", messages=msgs)
        assistant_reply = resp.choices[0].message.content
    except Exception as e:
        assistant_reply = f"⚠️ Error: {str(e)}"

    history.append({"role": "assistant", "content": assistant_reply})

    # Render chat bubbles
    bubbles = []
    for msg in history:
        is_user = msg["role"] == "user"
        avatar = html.Div([
            html.Img(src="/assets/logo.png",
                     style={"width":"22px","height":"22px","borderRadius":"50%",
                            "marginRight":"6px","verticalAlign":"middle"}),
            html.Span("AI", style={"fontSize":"10px","fontWeight":"700","color":MUT}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"3px"})

        label = html.Div("You", style={"fontSize":"10px","fontWeight":"700",
                                        "color":P,"marginBottom":"3px"}) if is_user else avatar

        body = (html.Div(msg["content"],
                         style={"background":"#EBF5FB","border":"1px solid #BDE0F0",
                                "borderRadius":"8px","padding":"10px 14px",
                                "fontSize":"13px","color":TXT,"lineHeight":"1.6"})
                if is_user else
                dcc.Markdown(msg["content"],
                             style={"background":"white","border":"1px solid #EEE",
                                    "borderRadius":"8px","padding":"10px 14px",
                                    "fontSize":"13px","color":TXT,"lineHeight":"1.6"},
                             dangerously_allow_html=False))

        bubbles.append(html.Div([label, body],
                                style={"marginBottom":"12px",
                                       "paddingLeft":"0" if is_user else "0",
                                       "paddingRight":"20px" if is_user else "0"}))

    return bubbles, history, ""


if __name__ == "__main__":
    app.run(debug=True, port=8050)
