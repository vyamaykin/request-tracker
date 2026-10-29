"""Department request tracker: where each department request sits in the dashboard process.

Streamlit UI. Data lives in Delta tables behind a Databricks SQL warehouse (see store.py).
"""
import html
from datetime import date, timedelta

import streamlit as st

from content import EXTRA_COLORS, QUESTIONS, STAGES, TIPS
from store import make_store

st.set_page_config(page_title="Department request tracker", layout="wide")

st.markdown("""
<style>
.trk-meta{display:flex;flex-wrap:wrap;gap:2px 12px;align-items:baseline;margin:0 0 6px}
.trk-stage{opacity:.7;font-size:14px}
.trk-pct{margin-left:auto;font-weight:800;font-size:20px}
.bar9{display:grid;grid-template-columns:repeat(9,1fr);gap:3px}
.seg{height:22px;background:rgba(128,128,128,.22);font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;opacity:.9}
.seg:first-child{border-radius:6px 0 0 6px}.seg:last-child{border-radius:0 6px 6px 0}
.seg.done{background:var(--c);color:#fff}
.seg.now{background:var(--c);color:#fff;box-shadow:inset 0 0 0 2px currentColor}
.trk-raci{display:flex;flex-wrap:wrap;gap:2px 16px;margin-top:8px;font-size:13px;opacity:.75}
.blk-badge{font-size:12px;font-weight:700;color:#fff;background:#D23B3B;border-radius:999px;padding:1px 8px}
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Connecting to Databricks...")
def get_store():
    return make_store()


@st.cache_data(ttl=20, show_spinner=False)
def load_data():
    s = get_store()
    return s.departments(), s.requests()


def current_user() -> str:
    # Databricks Apps puts the signed-in user's email in a proxy header
    try:
        return st.context.headers.get("X-Forwarded-Email") or "local"
    except Exception:
        return "local"


def write(fn, *args, **kwargs) -> bool:
    """Run a store write, refresh cached data, and show a clean error instead of a stack trace."""
    try:
        fn(*args, **kwargs)
    except ValueError as e:
        st.error(str(e))
        return False
    except Exception:
        st.error("Could not save to Databricks. Check the warehouse and table permissions, then try again.")
        return False
    load_data.clear()
    return True


try:
    store = get_store()
    departments, requests = load_data()
except Exception:
    st.error("Could not reach the Databricks backend. Check the SQL warehouse binding and the app's table permissions.")
    st.stop()

dept_by_name = {d["name"]: d for d in departments}
dept_names = list(dept_by_name)
user = current_user()

# ---------------------------------------------------------------- header
left, right = st.columns([3, 2], vertical_alignment="bottom")
with left:
    st.title("Department request tracker")
    st.caption("Where each department request sits in the dashboard process, and when it runs.")
with right:
    c1, c2 = st.columns(2)
    with c1, st.popover("Add department", use_container_width=True):
        with st.form("dept_form", clear_on_submit=True):
            new_dept = st.text_input("New department name", max_chars=40)
            if st.form_submit_button("Add department"):
                name = " ".join(new_dept.split())
                if name:
                    initials = "".join(w[0] for w in name.split()[:2]).upper()
                    color = EXTRA_COLORS[max(0, len(departments) - 4) % len(EXTRA_COLORS)]  # 4 seed departments have fixed colors
                    if write(store.add_department, name, initials, color):
                        st.session_state["shown"] = [*st.session_state.get("shown", dept_names), name]
                        st.rerun()
    with c2:
        if st.button("Add request", type="primary", use_container_width=True, disabled=not dept_names):
            today = date.today()
            rid = None
            try:
                rid = store.add_request(dept_names[0], "New request", "", 0, today, today + timedelta(days=90), "", user)
                load_data.clear()
                st.session_state["selected_id"] = rid
                st.rerun()
            except Exception:
                st.error("Could not save to Databricks. Check the warehouse and table permissions, then try again.")

if store.mode == "memory":
    st.warning("Demo mode: no SQL warehouse is configured, so changes are kept in memory and lost on restart.")

# ---------------------------------------------------------------- department filter
counts = {n: sum(r["dept"] == n for r in requests) for n in dept_names}
if "shown" not in st.session_state:
    st.session_state["shown"] = dept_names
st.session_state["shown"] = [d for d in st.session_state["shown"] if d in dept_by_name]
shown = st.pills("Show departments", dept_names, selection_mode="multi", key="shown",
                 format_func=lambda d: f"{d} ({counts[d]})")

sort = st.session_state.get("sort", "none")
visible = [r for r in requests if r["dept"] in shown]
if sort == "asc":
    visible.sort(key=lambda r: r["stage"])
elif sort == "desc":
    visible.sort(key=lambda r: -r["stage"])

visible_ids = [r["id"] for r in visible]
if st.session_state.get("selected_id") not in visible_ids:
    st.session_state["selected_id"] = visible_ids[0] if visible_ids else None
selected = next((r for r in requests if r["id"] == st.session_state["selected_id"]), None)


def select(rid):
    st.session_state["selected_id"] = rid


# ---------------------------------------------------------------- tracker + editor
tracker_col, editor_col = st.columns([1.35, 1], gap="large")

with tracker_col:
    with st.container(border=True):
        h, s = st.columns([3, 1.4], vertical_alignment="bottom")
        h.subheader("Progress through release stages")
        s.selectbox("Sort", ["none", "desc", "asc"], key="sort",
                    format_func={"none": "Order added", "desc": "Most complete first", "asc": "Least complete first"}.get)
        st.markdown("\n".join(f"{i + 1}. {stg['name']}" for i, stg in enumerate(STAGES)))
        if not visible:
            st.info("No requests shown. Turn on a department above or add a request.")
        for r in visible:
            d = dept_by_name.get(r["dept"], {"color": "#888"})
            stg = STAGES[r["stage"]]
            pct = round((r["stage"] + 1) / len(STAGES) * 100)
            nb = len(r["blockers"])
            is_sel = r["id"] == st.session_state["selected_id"]
            with st.container(border=True):
                st.button(("● " if is_sel else "") + r["name"], key=f"pick_{r['id']}", type="tertiary",
                          on_click=select, args=(r["id"],))
                segs = "".join(
                    f'<span class="seg{" done" if i < r["stage"] else " now" if i == r["stage"] else ""}">{i + 1}</span>'
                    for i in range(len(STAGES)))
                badge = f'<span class="blk-badge">{nb} blocker{"s" if nb > 1 else ""}</span>' if nb else ""
                st.markdown(f"""
<div style="--c:{html.escape(d['color'])}">
  <div class="trk-meta"><span class="trk-stage">{html.escape(r['dept'])}, stage {r['stage'] + 1} of 9: {html.escape(stg['name'])}</span>{badge}<span class="trk-pct">{pct}%</span></div>
  <div class="bar9">{segs}</div>
  <div class="trk-raci"><span>Responsible: <b>{stg['r']}</b></span><span>Accountable: <b>{stg['a']}</b></span><span>Typical timing: <b>{stg['when']}</b></span></div>
</div>""", unsafe_allow_html=True)

with editor_col:
    with st.container(border=True):
        st.subheader("Requests")
        if not selected:
            st.caption("Pick a request to edit its stage and dates.")
        else:
            rid = selected["id"]
            st.selectbox("Request", visible_ids, key="selected_id",
                         format_func=lambda i: next(r["name"] for r in requests if r["id"] == i))
            st.markdown("**Edit request**")

            # Stage saves immediately, like clicking a segment on the bar
            def set_stage(rid=rid, key=f"stage_{rid}_{selected['stage']}"):
                value = st.session_state.get(key)
                if value:
                    write(store.update_request, rid, user, stage=value - 1)

            st.segmented_control("Current stage", list(range(1, len(STAGES) + 1)), default=selected["stage"] + 1,
                                 key=f"stage_{rid}_{selected['stage']}", on_change=set_stage)
            st.caption(f"Stage {selected['stage'] + 1}: {STAGES[selected['stage']]['name']}")

            with st.form(f"edit_{rid}_{selected['name']}_{selected['dept']}"):
                name = st.text_input("Name", selected["name"])
                f1, f2 = st.columns(2)
                dept = f1.selectbox("Department", dept_names,
                                    index=dept_names.index(selected["dept"]) if selected["dept"] in dept_names else 0)
                jira = f2.text_input("Jira key", selected["jira"], placeholder="GDL-123")
                d1, d2 = st.columns(2)
                start = d1.date_input("Start", selected["start"])
                end = d2.date_input("Target end", selected["end"])
                notes = st.text_area("Notes", selected["notes"], height=80)
                if st.form_submit_button("Save changes", type="primary"):
                    if not name.strip():
                        st.error("Name is required.")
                    else:
                        if end < start:
                            end = start
                        if write(store.update_request, rid, user, name=name.strip(), dept=dept, jira=jira.strip(),
                                 start=start, end=end, notes=notes):
                            st.rerun()

            st.markdown("**Blockers**")
            if not selected["blockers"]:
                st.caption("No blockers.")
            for b in selected["blockers"]:
                t, x = st.columns([5, 1], vertical_alignment="center")
                t.markdown(f":red[{b['text']}]")
                if x.button("Remove", key=f"rmblk_{b['id']}", type="tertiary"):
                    if write(store.remove_blocker, b["id"]):
                        st.rerun()
            with st.form(f"blk_{rid}", clear_on_submit=True, border=False):
                text = st.text_input("New blocker", placeholder="Describe what is blocking progress",
                                     label_visibility="collapsed")
                if st.form_submit_button("Add blocker") and text.strip():
                    if write(store.add_blocker, rid, text.strip(), user):
                        st.rerun()

            with st.popover("Delete request"):
                st.warning(f"Delete \"{selected['name']}\" and its blockers? This cannot be undone.")
                if st.button("Yes, delete", key=f"del_{rid}"):
                    if write(store.delete_request, rid):
                        st.rerun()

# ---------------------------------------------------------------- stage questions
with st.container(border=True):
    st.subheader("Questions for each stage")
    open_stage = selected["stage"] if selected else None
    for i, stg in enumerate(STAGES):
        groups = QUESTIONS[i]
        n = sum(len(q) for q in groups.values())
        with st.expander(f"{i + 1}. {stg['name']}  ·  {stg['when']}  ·  {n} questions", expanded=(i == open_stage)):
            cols = st.columns(min(len(groups), 3))
            for j, (who, qs) in enumerate(groups.items()):
                with cols[j % len(cols)]:
                    st.markdown(f"**{who}**")
                    st.markdown("\n".join(f"- {q}" for q in qs))
            if i in TIPS:
                st.info(f"**Tip:** {TIPS[i]}")
