import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
random.seed(42)
np.random.seed(42)
Faker.seed(42)

REGIONS = ["Central", "West", "South", "East", "North", "Southwest", "Intermountain"]
STATUSES = ["Planning", "In Progress", "On Hold", "Completed"]
PROJECT_TYPES = ["Infrastructure", "Residential", "Commercial", "Industrial"]
PHASES = ["Foundation", "Design", "Structure", "Finishing", "Closeout"]
DEPARTMENTS = ["Safety", "Procurement", "Engineering", "Project Management"]
CONTRACTORS = [
    "Williams LLC", "White-Kelly", "Roth PLC", "Williams, Black and Gomez",
    "Webster, Smith and Pope", "Soto, Wyatt and Sharp", "Watts-Meadows",
    "Nixon-Wiggins", "Davis, Bowman and Baird", "Robles-Wilson", "Cross LLC", "Bender-Waters"
]
ELECTRICAL_PROJECT_NAMES = [
    "Data Center", "Substation Upgrade", "Transmission Line", "Power Delivery",
    "Grid Modernization", "Switchgear Install", "HV Cable Project", "Feeder Extension",
    "Renewable Integration", "Microgrid", "Underground Distribution", "Transformer Bank"
]

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_projects(n=500):
    rows = []
    for i in range(n):
        budget = round(random.uniform(3000, 15000), 1)
        cost_pct = random.uniform(0.3, 1.15)
        cost = round(budget * cost_pct, 1)
        start = fake.date_between(start_date="-2y", end_date="-1m")
        end = start + timedelta(days=random.randint(30, 540))
        status = random.choice(STATUSES)
        region = random.choice(REGIONS)
        proj_type = random.choice(PROJECT_TYPES)
        phase = random.choice(PHASES)
        dept = random.choice(DEPARTMENTS)
        contractor = random.choice(CONTRACTORS)
        budget_status = "Over Budget" if cost > budget else "Within Budget"
        name_prefix = random.choice(ELECTRICAL_PROJECT_NAMES)
        rows.append({
            "ID": i + 1,
            "Project Name": f"{name_prefix} {i+1}",
            "Project Type": proj_type,
            "Region": region,
            "Status": status,
            "Phase": phase,
            "Department": dept,
            "Contractor": contractor,
            "Budget": budget,
            "Cost": cost,
            "Budget Status": budget_status,
            "Start Date": start.strftime("%Y-%m-%d"),
            "End Date": end.strftime("%Y-%m-%d"),
            "Month": start.strftime("%b"),
            "Month_Num": start.month,
            "Year": start.year,
            "Safety Incidents": random.randint(0, 8),
            "Crew Size": random.randint(8, 60),
            "Days Remaining": max(0, (end - datetime.now().date()).days),
            "Schedule Variance (%)": round(random.uniform(-15, 20), 1),
            "Change Orders": random.randint(0, 12),
            "RFIs Open": random.randint(0, 18),
            "Punch List Items": random.randint(0, 55),
        })
    df = pd.DataFrame(rows)
    return df


df_raw = generate_projects(500)
