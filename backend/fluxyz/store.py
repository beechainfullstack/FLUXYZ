import re
from datetime import datetime, timedelta, timezone
from typing import cast

import pymysql
from pydantic import BaseModel
from pymysql.cursors import DictCursor

from fluxyz.models import CoalReference, Observation, Price, Signal, SourceHealth
from fluxyz.settings import settings

SCHEMA = {
    "commodity_prices": (
        "commodity VARCHAR(20), timestamp DATETIME, price DOUBLE, volume DOUBLE NULL, "
        "source VARCHAR(40)",
        "commodity, timestamp",
    ),
    "coal_reference": (
        "timestamp DATETIME, price DOUBLE, period VARCHAR(10), units VARCHAR(80), "
        "description VARCHAR(255), source VARCHAR(40)",
        "timestamp",
    ),
    "universal_signals": (
        "timestamp DATETIME, days_to_solstice DOUBLE, days_to_event DOUBLE, "
        "nearest_event VARCHAR(60), event_timestamp DATETIME, kp_index DOUBLE NULL, "
        "kp_timestamp DATETIME NULL, solar_flare_class VARCHAR(12) NULL, "
        "solar_timestamp DATETIME NULL, flare_peak_class VARCHAR(12) NULL, "
        "flare_peak_timestamp DATETIME NULL",
        "timestamp",
    ),
    "observations": (
        "id VARCHAR(36), timestamp DATETIME, `text` STRING, model VARCHAR(60), kind VARCHAR(30)",
        "id",
    ),
    "source_health": (
        "source VARCHAR(40), status VARCHAR(20), last_attempt DATETIME NULL, "
        "last_success DATETIME NULL, message VARCHAR(255)",
        "source",
    ),
}


def connection(database: bool = True) -> pymysql.Connection:
    return pymysql.connect(
        host=settings.starrocks_host,
        port=settings.starrocks_port,
        user=settings.starrocks_user,
        password=settings.starrocks_password,
        database=settings.starrocks_database if database else None,
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )


def initialize() -> None:
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", settings.starrocks_database):
        raise ValueError("Invalid database name")
    with connection(False) as db, db.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.starrocks_database}`")
        cursor.execute(f"USE `{settings.starrocks_database}`")
        for table, (columns, keys) in SCHEMA.items():
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({columns}) "
                f"PRIMARY KEY ({keys}) DISTRIBUTED BY HASH ({keys.split(',')[0]}) "
                'BUCKETS 1 PROPERTIES ("replication_num"="1")'
            )


def query(sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    with connection() as db, db.cursor() as cursor:
        cursor.execute(sql, params)
        return cast(list[dict[str, object]], list(cursor.fetchall()))


def save(table: str, records: list[BaseModel]) -> None:
    if table not in SCHEMA or not records:
        return
    columns = list(records[0].model_dump())
    column_sql = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    rows = []
    for record in records:
        row = record.model_dump()
        rows.append(
            tuple(
                row[key].astimezone(timezone.utc).replace(tzinfo=None)
                if isinstance(row[key], datetime)
                else row[key]
                for key in columns
            )
        )
    with connection() as db, db.cursor() as cursor:
        cursor.executemany(f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})", rows)


def prices() -> list[Price]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=35)
    return [
        Price.model_validate(row)
        for row in query(
            "SELECT * FROM commodity_prices WHERE timestamp >= %s ORDER BY timestamp", (since,)
        )
    ]


def signals() -> list[Signal]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=35)
    return [
        Signal.model_validate(row)
        for row in query(
            "SELECT * FROM universal_signals WHERE timestamp >= %s ORDER BY timestamp", (since,)
        )
    ]


def latest_coal() -> CoalReference | None:
    rows = query("SELECT * FROM coal_reference ORDER BY timestamp DESC LIMIT 1")
    return CoalReference.model_validate(rows[0]) if rows else None


def observations() -> list[Observation]:
    return [
        Observation.model_validate(row)
        for row in query("SELECT * FROM observations ORDER BY timestamp DESC LIMIT 25")
    ]


def sources() -> list[SourceHealth]:
    return [SourceHealth.model_validate(row) for row in query("SELECT * FROM source_health")]
