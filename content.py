"""Static content for the Department request tracker: release stages, discovery questions, seed data.

Ported from the original single-file HTML tracker. Nothing here touches Databricks.
"""

# 9 release stages with Responsible / Accountable and typical timing
STAGES = [
    {"name": "Request & Intake",               "r": "End users",  "a": "Executive stakeholders", "when": "Week 1"},
    {"name": "Requirements & Design",          "r": "Developers", "a": "Executive stakeholders", "when": "Weeks 1 to 3"},
    {"name": "Build",                          "r": "Developers", "a": "Developers",             "when": "Weeks 3 to 9"},
    {"name": "QA & Validation",                "r": "Developers", "a": "Developers",             "when": "Weeks 9 to 12"},
    {"name": "Stakeholder Review & Approval",  "r": "End users",  "a": "Executive stakeholders", "when": "Weeks 11 to 12"},
    {"name": "Release",                        "r": "Developers", "a": "Developers",             "when": "Week 12"},
    {"name": "Training & Enablement",          "r": "Developers", "a": "Developers",             "when": "Weeks 12 to 13"},
    {"name": "Monitoring & Maintenance",       "r": "Developers", "a": "Developers",             "when": "Ongoing"},
    {"name": "Review, Iteration & Retirement", "r": "Developers", "a": "Executive stakeholders", "when": "Ongoing"},
]

# Colors handed out to departments added in the app, in order
EXTRA_COLORS = ["#5B6BD6", "#8C6D1F", "#1F8FBF", "#9A3FA8", "#4F8A10", "#B04A3A", "#2F6F8F", "#A0522D"]

SEED_DEPARTMENTS = [
    {"name": "Retail",       "short": "R",  "color": "#C08A00"},
    {"name": "Excel Center", "short": "EC", "color": "#7A3FD6"},
    {"name": "HR",           "short": "HR", "color": "#C7317A"},
    {"name": "Contracts",    "short": "C",  "color": "#0E7C70"},
]

# One epic per department. Stages (0-based) and dates are editable starting points.
SEED_REQUESTS = [
    {"dept": "Retail",       "name": "Retail - New",                    "jira": "GDL-947", "stage": 2, "start": "2026-05-21", "end": "2026-11-30"},
    {"dept": "Excel Center", "name": "Excel Center Report Development", "jira": "GDL-128", "stage": 3, "start": "2025-07-18", "end": "2026-11-30"},
    {"dept": "HR",           "name": "HR reporting",                    "jira": "",        "stage": 0, "start": "2026-11-02", "end": "2027-02-01"},
    {"dept": "Contracts",    "name": "Contract Report Portal",          "jira": "",        "stage": 0, "start": "2026-10-28", "end": "2027-01-29"},
]

# Questions per stage (index = stage), grouped by who answers them.
QUESTIONS = [
    {"Current state": ["Walk me through how a report gets made and shared today, start to finish.", "What's slow, manual, or error-prone?", "Which tools and files are involved?"],
     "Users and goals": ["Who will use it, and how often?", "What business question should it answer?", "What would make this a success for you?"],
     "Data and constraints": ["Where does the data come from, and who owns it?", "What are the deadlines, budget limits, or system dependencies?"],
     "Open questions and next steps": ["What haven't we asked that we should have?", "Who else should we talk to?"],
     "Developers": ["Is request logged in Jira?", "Do needed data sources exist, and can we access them?", "What is rough effort estimate?"],
     "End users": ["Is request submitted in Jira with business justification?"],
     "Executive stakeholders": ["How does request rank against department priorities?", "Approve for development queue, or decline with reasoning?"]},
    {"User research": ["What challenges and frustrations do users have?", "What are the top 3 things they need to do?", "What do they already know about the data? What do they need to know?"],
     "Goals and scope": ["What actions would team take based on this report?", "Which reports matter most? Which can wait?", "How will we measure success, such as usage or time saved?"],
     "Data": ["What calculations are needed?", "How fresh must the data be, and how often should it refresh?"],
     "Layout and features": ["What is report or dashboard title?", "Where will it be viewed: desktop, large TV display, mobile?", "What filters do people need?", "What exports do people need?", "Any accessibility needs, such as screen readers, color contrast, or text size?"],
     "Access and compliance": ["Who should have access?", "Are there approval, audit, or compliance requirements?"],
     "Sign-off": ["Is every metric definition confirmed, with no ambiguity on what number means?", "Has wireframe been reviewed, including missing filters, breakdowns, or views?", "Has executive signed off on scope before build?"]},
    {"Developers": ["Are gateways, settings, and failure notifications set up?", "Which date ranges are used most (for date table)?", "Is row-level security set up to match agreed access?", "Is refresh schedule set?", "Is quick-win MVP (1 to 2 pages) ready by week 4?", "Is Knowledge Based Article (KBA) up to date?"],
     "End users": ["Are clarifying questions from developers answered?"]},
    {"Developers": ["Do numbers match source systems and AMI?", "In Staging, does report refresh and show correct totals?", "Did performance and load testing pass?", "Are QA defects fixed?"],
     "End users": ["Was UAT run against known scenarios?", "Do numbers match existing reporting you trust?", "Which reliability bucket fits: unreliable, reliable with caveats, or endorsed?"]},
    {"Developers": ["Were finished report and QA results presented?", "Does it meet data governance and access policy?"],
     "End users": ["Is formal sign-off given that it is fit for use?"],
     "Executive stakeholders": ["Does it align with strategic priorities and governance standards?", "Is release approved?"]},
    {"Developers": ["Is it published to production in Power BI App?", "Are final access permissions set?", "Is it added to report catalog?", "Is distribution list notified?"],
     "End users": ["Can you access live report?", "Any issues right after launch?"],
     "Executive stakeholders": ["Has availability been announced to wider department?"]},
    {"Developers": ["Is end-user documentation provided?", "Did handover session (1 to 2 hours) happen within 1 week of sign-off?", "Are usage metrics shared with leadership?"],
     "End users": ["Did team attend walkthrough?", "What early usability feedback came up?"],
     "Executive stakeholders": ["Is team encouraged to adopt it?", "Is it reinforced as source of truth for this area?"]},
    {"Developers": ["Is pipeline healthy and data fresh?", "Which bugs need triage?", "Which enhancement requests are scoped for next sprint?"],
     "End users": ["What feedback or change requests do you have?"],
     "Executive stakeholders": ["When is next usage and value review (for example, quarterly)?", "Are success measures agreed at design being met?"]},
    {"Developers": ["Do changed requirements need version update?", "Is usage low or a data source stale?"],
     "End users": ["Is dashboard still needed in current form?"],
     "Executive stakeholders": ["Approve retirement or major re-scope?"]},
]

# Optional tip shown at the bottom of a stage section (index = stage)
TIPS = {0: "Ask open-ended questions and listen more than you talk. Discovery is about learning, not solving yet."}
