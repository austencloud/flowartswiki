"""MariaDB connection helpers for LinkKeeper."""

import pymysql
import pymysql.cursors

_pool = None


def get_connection(config):
    """Get a MariaDB connection using config dict."""
    return pymysql.connect(
        host=config["db_host"],
        port=config.get("db_port", 3306),
        user=config["db_user"],
        password=config["db_password"],
        database=config["db_name"],
        charset="binary",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )


def execute(conn, sql, params=None):
    """Execute a query and return all rows."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute_one(conn, sql, params=None):
    """Execute a query and return one row."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute_insert(conn, sql, params=None):
    """Execute an insert and return lastrowid."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


def execute_many(conn, sql, params_list):
    """Execute a query with many parameter sets."""
    with conn.cursor() as cur:
        cur.executemany(sql, params_list)
        return cur.rowcount


def now_ts():
    """Return current UTC timestamp in MediaWiki format (YYYYMMDDHHmmss)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
