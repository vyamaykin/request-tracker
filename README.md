# Department request tracker

Streamlit app (Databricks App) that tracks where each department request sits in the 9-stage dashboard
release process. Ported from the single-file HTML tracker; data now lives in Delta tables instead of
browser storage, so everyone sees the same state.

## Layout

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI: department filter, stage bars, editor, blockers, per-stage questions |
| `store.py` | Persistence. `DatabricksStore` (SQL warehouse + Delta) and `MemoryStore` (demo) |
| `content.py` | Static content: stages, questions, seed data |
| `app.yaml` | Databricks Apps config (warehouse binding, catalog/schema) |

## Backend

The app calls a SQL warehouse with parameterized SQL and creates three tables on first run in
`TRACKER_CATALOG.TRACKER_SCHEMA` (default `gold.retail_data_science`, set in `app.yaml`):

- `request_tracker_departments` (name, short, color, sort_order)
- `request_tracker_requests` (id, dept, name, jira, stage 0-8, start_date, end_date, notes, created_at, updated_at, updated_by)
- `request_tracker_blockers` (id, request_id, text, created_at, created_by)

Seed departments and requests are inserted only when the departments table is empty. `updated_by` is the
signed-in user's email from the Databricks Apps proxy header.

With no warehouse configured the app runs in **demo mode** (in-memory data, banner shown).

## Deploy

1. Create the app and bind a SQL warehouse resource named `sql-warehouse` (CAN_USE).
2. Grant the app's service principal on the target schema: `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`
   (first run only), and `SELECT` + `MODIFY` on the three tables. Missing `USE CATALOG`/`USE SCHEMA` gives
   `INSUFFICIENT_PERMISSIONS` even when table grants look right.
3. `databricks apps deploy <app-name> --mode SNAPSHOT` (git-bound) or from a workspace source path.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py                      # demo mode, in-memory
DATABRICKS_WAREHOUSE_ID=<id> streamlit run app.py   # real tables; needs `databricks auth login` (profile DEFAULT)
```

## Tests

```bash
pip install pytest && python -m pytest tests
```
