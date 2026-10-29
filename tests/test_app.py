"""Run from the project root: python -m pytest tests  (or python tests/test_app.py)."""
import os
import sys
from contextlib import contextmanager
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TRACKER_BACKEND"] = "memory"

import pytest
from streamlit.testing.v1 import AppTest

from store import DatabricksStore, MemoryStore


def test_memory_store_crud():
    s = MemoryStore()
    assert [d["name"] for d in s.departments()] == ["Retail", "Excel Center", "HR", "Contracts"]
    rid = s.add_request("HR", "X", "", 0, date(2026, 1, 1), date(2026, 2, 1), "", "me")
    s.update_request(rid, "me", stage=4)
    s.add_blocker(rid, "waiting on data", "me")
    req = next(r for r in s.requests() if r["id"] == rid)
    assert req["stage"] == 4 and req["blockers"][0]["text"] == "waiting on data"
    s.remove_blocker(req["blockers"][0]["id"])
    s.delete_request(rid)
    assert all(r["id"] != rid for r in s.requests())
    with pytest.raises(ValueError):
        s.add_department("hr", "H", "#000")


class FakeCursor:
    def __init__(self, log):
        self.log, self.description = log, [("n",)]

    def execute(self, sql, params=None):
        self.log.append((" ".join(sql.split()), params))

    def fetchone(self):
        return (0,)

    def fetchall(self):
        return []


def make_fake_store():
    log = []
    store = DatabricksStore("abc123", "gold", "sch")

    @contextmanager
    def cursor():
        yield FakeCursor(log)

    store._cursor = cursor
    return store, log


def test_databricks_sql_is_parameterized():
    store, log = make_fake_store()
    evil = "x'; DROP TABLE t; --"
    store.update_request("id1", "me", name=evil, stage=2)
    sql, params = log[-1]
    assert evil not in sql and params["name"] == evil
    assert sql.startswith("UPDATE `gold`.`sch`.`request_tracker_requests` SET name = :name, stage = :stage")
    with pytest.raises(ValueError):
        store.update_request("id1", "me", **{"name = 'x', id": "y"})
    with pytest.raises(ValueError):
        DatabricksStore("abc", "gold", "sch`; DROP")


def test_ensure_tables_creates_and_seeds():
    store, log = make_fake_store()
    store.ensure_tables()
    statements = [s for s, _ in log]
    assert sum(s.startswith("CREATE TABLE IF NOT EXISTS") for s in statements) == 3
    assert sum("INSERT INTO `gold`.`sch`.`request_tracker_departments`" in s for s in statements) == 4
    assert sum("INSERT INTO `gold`.`sch`.`request_tracker_requests`" in s for s in statements) == 4


def test_app_renders_and_edits():
    at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.warning[0].value.startswith("Demo mode")
    assert [e.label.split("  ")[0] for e in at.expander][:2] == ["1. Request & Intake", "2. Requirements & Design"]
    # jump the selected request to stage 6 through the stage control
    seg = next(g for g in at.get("button_group") if g.key.startswith("stage_"))
    seg.set_value(6).run()
    assert not at.exception
    assert any("stage 6 of 9: Release" in m.value for m in at.markdown)
    # add a blocker to it
    at.text_input[-1].set_value("Need access").run()
    next(b for b in at.button if b.label == "Add blocker").click().run()
    assert not at.exception
    assert any("Need access" in m.value for m in at.markdown)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
