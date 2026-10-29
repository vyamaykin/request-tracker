"""Persistence for the Department request tracker.

Two interchangeable backends with the same methods:
  * DatabricksStore - Delta tables read and written through a SQL warehouse.
  * MemoryStore     - in-process demo data, used when no warehouse is configured.

Neither imports Streamlit, so both can be tested on their own.
"""
import os
import re
import uuid
from contextlib import contextmanager
from datetime import date

from content import SEED_DEPARTMENTS, SEED_REQUESTS

_IDENT = re.compile(r"[A-Za-z0-9_]+")
TABLE_PREFIX = "request_tracker_"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _iso(d) -> date | None:
    return date.fromisoformat(d) if isinstance(d, str) and d else (d or None)


# --------------------------------------------------------------------------- memory

class MemoryStore:
    mode = "memory"

    def __init__(self):
        self._depts = [dict(d) for d in SEED_DEPARTMENTS]
        self._reqs = []
        for r in SEED_REQUESTS:
            self._reqs.append({**r, "id": _new_id(), "notes": "", "blockers": [],
                               "start": _iso(r["start"]), "end": _iso(r["end"])})

    def departments(self):
        return [dict(d) for d in self._depts]

    def add_department(self, name, short, color):
        if any(d["name"].lower() == name.lower() for d in self._depts):
            raise ValueError(f"{name} already exists")
        self._depts.append({"name": name, "short": short, "color": color})

    def requests(self):
        return [{**r, "blockers": [dict(b) for b in r["blockers"]]} for r in self._reqs]

    def add_request(self, dept, name, jira, stage, start, end, notes, user):
        rid = _new_id()
        self._reqs.append({"id": rid, "dept": dept, "name": name, "jira": jira, "stage": stage,
                           "start": start, "end": end, "notes": notes, "blockers": []})
        return rid

    def update_request(self, rid, user, **fields):
        for r in self._reqs:
            if r["id"] == rid:
                r.update(fields)
                return

    def delete_request(self, rid):
        self._reqs = [r for r in self._reqs if r["id"] != rid]

    def add_blocker(self, rid, text, user):
        for r in self._reqs:
            if r["id"] == rid:
                r["blockers"].append({"id": _new_id(), "text": text})

    def remove_blocker(self, bid):
        for r in self._reqs:
            r["blockers"] = [b for b in r["blockers"] if b["id"] != bid]


# --------------------------------------------------------------------------- databricks

# request fields the app may update, mapped to column names
_COLUMNS = {"dept": "dept", "name": "name", "jira": "jira", "stage": "stage",
            "start": "start_date", "end": "end_date", "notes": "notes"}


class DatabricksStore:
    mode = "databricks"

    def __init__(self, warehouse_id: str, catalog: str, schema: str):
        for part in (warehouse_id, catalog, schema):
            if not _IDENT.fullmatch(part):
                raise ValueError(f"Invalid identifier: {part!r}")
        self._http_path = f"/sql/1.0/warehouses/{warehouse_id}"
        ns = f"`{catalog}`.`{schema}`"
        self.t_dept = f"{ns}.`{TABLE_PREFIX}departments`"
        self.t_req = f"{ns}.`{TABLE_PREFIX}requests`"
        self.t_blk = f"{ns}.`{TABLE_PREFIX}blockers`"
        self._cfg = None

    @contextmanager
    def _cursor(self):
        # Imported lazily so the app still starts in memory mode without these packages.
        from databricks import sql
        from databricks.sdk.core import Config

        if self._cfg is None:
            self._cfg = Config()  # service principal in Databricks Apps, CLI profile locally
        cfg = self._cfg
        with sql.connect(
            server_hostname=cfg.host.removeprefix("https://").rstrip("/"),
            http_path=self._http_path,
            credentials_provider=lambda: cfg.authenticate,
        ) as conn:
            with conn.cursor() as cur:
                yield cur

    @staticmethod
    def _rows(cur):
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _exec(self, statement, params=None):
        with self._cursor() as cur:
            cur.execute(statement, params or {})

    def ensure_tables(self):
        """Create the tables on first run and seed the starting departments and requests."""
        with self._cursor() as cur:
            cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.t_dept} (
                name STRING, short STRING, color STRING, sort_order INT) USING DELTA""")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.t_req} (
                id STRING, dept STRING, name STRING, jira STRING, stage INT,
                start_date DATE, end_date DATE, notes STRING,
                created_at TIMESTAMP, updated_at TIMESTAMP, updated_by STRING) USING DELTA""")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.t_blk} (
                id STRING, request_id STRING, text STRING,
                created_at TIMESTAMP, created_by STRING) USING DELTA""")
            cur.execute(f"SELECT COUNT(*) FROM {self.t_dept}")
            seeded = cur.fetchone()[0] > 0
            if not seeded:
                for i, d in enumerate(SEED_DEPARTMENTS):
                    cur.execute(f"INSERT INTO {self.t_dept} VALUES (:n, :s, :c, :o)",
                                {"n": d["name"], "s": d["short"], "c": d["color"], "o": i})
                for r in SEED_REQUESTS:
                    cur.execute(
                        f"""INSERT INTO {self.t_req} VALUES (:id, :dept, :name, :jira, :stage,
                            :start, :end, '', current_timestamp(), current_timestamp(), 'seed')""",
                        {"id": _new_id(), "dept": r["dept"], "name": r["name"], "jira": r["jira"],
                         "stage": r["stage"], "start": _iso(r["start"]), "end": _iso(r["end"])})

    def departments(self):
        with self._cursor() as cur:
            cur.execute(f"SELECT name, short, color FROM {self.t_dept} ORDER BY sort_order, name")
            return self._rows(cur)

    def add_department(self, name, short, color):
        with self._cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.t_dept} WHERE lower(name) = lower(:n)", {"n": name})
            if cur.fetchone()[0]:
                raise ValueError(f"{name} already exists")
            cur.execute(f"INSERT INTO {self.t_dept} SELECT :n, :s, :c, COALESCE(MAX(sort_order), -1) + 1 FROM {self.t_dept}",
                        {"n": name, "s": short, "c": color})

    def requests(self):
        with self._cursor() as cur:
            cur.execute(f"""SELECT id, dept, name, jira, stage, start_date AS start, end_date AS end, notes
                            FROM {self.t_req} ORDER BY created_at, id""")
            reqs = self._rows(cur)
            cur.execute(f"SELECT id, request_id, text FROM {self.t_blk} ORDER BY created_at, id")
            blockers = self._rows(cur)
        by_req = {}
        for b in blockers:
            by_req.setdefault(b["request_id"], []).append({"id": b["id"], "text": b["text"]})
        for r in reqs:
            r["jira"] = r["jira"] or ""
            r["notes"] = r["notes"] or ""
            r["blockers"] = by_req.get(r["id"], [])
        return reqs

    def add_request(self, dept, name, jira, stage, start, end, notes, user):
        rid = _new_id()
        self._exec(
            f"""INSERT INTO {self.t_req} VALUES (:id, :dept, :name, :jira, :stage, :start, :end,
                :notes, current_timestamp(), current_timestamp(), :user)""",
            {"id": rid, "dept": dept, "name": name, "jira": jira, "stage": stage,
             "start": start, "end": end, "notes": notes, "user": user})
        return rid

    def update_request(self, rid, user, **fields):
        unknown = set(fields) - set(_COLUMNS)
        if unknown:
            raise ValueError(f"Unknown fields: {sorted(unknown)}")
        sets = ", ".join(f"{_COLUMNS[k]} = :{k}" for k in fields)
        self._exec(
            f"UPDATE {self.t_req} SET {sets}, updated_at = current_timestamp(), updated_by = :user WHERE id = :id",
            {**fields, "user": user, "id": rid})

    def delete_request(self, rid):
        with self._cursor() as cur:
            cur.execute(f"DELETE FROM {self.t_blk} WHERE request_id = :id", {"id": rid})
            cur.execute(f"DELETE FROM {self.t_req} WHERE id = :id", {"id": rid})

    def add_blocker(self, rid, text, user):
        self._exec(f"INSERT INTO {self.t_blk} VALUES (:id, :rid, :text, current_timestamp(), :user)",
                   {"id": _new_id(), "rid": rid, "text": text, "user": user})

    def remove_blocker(self, bid):
        self._exec(f"DELETE FROM {self.t_blk} WHERE id = :id", {"id": bid})


def make_store():
    """Databricks when a warehouse is configured (or TRACKER_BACKEND=databricks), otherwise memory."""
    backend = os.environ.get("TRACKER_BACKEND", "").lower()
    warehouse = os.environ.get("DATABRICKS_WAREHOUSE_ID") or \
        os.environ.get("DATABRICKS_HTTP_PATH", "").rsplit("/", 1)[-1]
    if backend == "memory" or (backend != "databricks" and not warehouse):
        return MemoryStore()
    store = DatabricksStore(warehouse, os.environ.get("TRACKER_CATALOG", "gold"),
                            os.environ.get("TRACKER_SCHEMA", "retail_data_science"))
    store.ensure_tables()
    return store
