import json
import os
import sqlite3
from pathlib import Path

from database import DB

BASE_DIR = Path(__file__).resolve().parent
SEED_DIR = BASE_DIR / "seed"
ACCOUNTS_SEED_PATH = SEED_DIR / "accounts.seed.json"
LOGS_SEED_PATH = SEED_DIR / "logs.seed.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_seed_metadata() -> dict:
    metadata = {
        "data_source": "Runtime DB",
        "seed_version": "-",
        "seed_snapshot_utc": "-",
    }
    try:
        payload = _load_json(ACCOUNTS_SEED_PATH)
    except FileNotFoundError:
        return metadata

    metadata["data_source"] = "Seeded replay JSON"
    metadata["seed_version"] = payload.get("version", "-")
    metadata["seed_snapshot_utc"] = payload.get("snapshot_utc", "-")
    return metadata


def _db_counts() -> tuple[int, int]:
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM accounts")
        accounts_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM logs")
        logs_count = int(cur.fetchone()[0])
    return accounts_count, logs_count


def _insert_accounts(payload: dict) -> int:
    rows = payload.get("accounts", [])
    count = 0
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        for row in rows:
            name = str(row["name"]).lower()
            account_json = json.dumps(row["account"])
            cur.execute(
                """
                INSERT INTO accounts (name, account)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET account=excluded.account
                """,
                (name, account_json),
            )
            count += 1
        conn.commit()
    return count


def _insert_logs(payload: dict, reset: bool) -> int:
    rows = payload.get("logs", [])
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        if reset:
            cur.execute("DELETE FROM logs")
        cur.executemany(
            """
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    str(row["name"]).lower(),
                    row["datetime"],
                    row["type"],
                    row["message"],
                )
                for row in rows
            ],
        )
        conn.commit()
    return len(rows)


def seed_from_json(strategy: str = "if_empty") -> dict:
    strategy = strategy.strip().lower()
    if strategy not in {"if_empty", "always"}:
        strategy = "if_empty"

    accounts_payload = _load_json(ACCOUNTS_SEED_PATH)
    logs_payload = _load_json(LOGS_SEED_PATH)
    before_accounts, before_logs = _db_counts()
    should_seed = strategy == "always" or (before_accounts == 0 and before_logs == 0)

    if not should_seed:
        return {
            "seeded": False,
            "reason": "already-populated",
            "before_accounts": before_accounts,
            "before_logs": before_logs,
            "after_accounts": before_accounts,
            "after_logs": before_logs,
            "version": accounts_payload.get("version", "-"),
            "snapshot_utc": accounts_payload.get("snapshot_utc", "-"),
        }

    inserted_accounts = _insert_accounts(accounts_payload)
    inserted_logs = _insert_logs(logs_payload, reset=(strategy == "always"))
    after_accounts, after_logs = _db_counts()
    return {
        "seeded": True,
        "reason": strategy,
        "inserted_accounts": inserted_accounts,
        "inserted_logs": inserted_logs,
        "before_accounts": before_accounts,
        "before_logs": before_logs,
        "after_accounts": after_accounts,
        "after_logs": after_logs,
        "version": accounts_payload.get("version", "-"),
        "snapshot_utc": accounts_payload.get("snapshot_utc", "-"),
    }


def maybe_seed_on_startup() -> dict:
    seed_on_startup = os.getenv("SEED_ON_STARTUP", "true").strip().lower() == "true"
    strategy = os.getenv("SEED_STRATEGY", "if_empty")
    if not seed_on_startup:
        return {"seeded": False, "reason": "disabled"}
    return seed_from_json(strategy=strategy)
