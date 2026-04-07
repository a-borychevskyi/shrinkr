import re
import time

from loguru import logger
from prometheus_client import Counter, Histogram
from sqlalchemy import event
from sqlalchemy.engine import Engine

_OPERATION_RE = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b", re.IGNORECASE
)
_TABLE_RE = re.compile(
    r"(?:FROM|INTO|UPDATE|JOIN)\s+([\"']?\w+[\"']?)", re.IGNORECASE
)

sql_query_duration = Histogram(
    "sql_query_duration_seconds",
    "Time spent executing SQL queries",
    labelnames=["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

sql_query_total = Counter(
    "sql_query_total",
    "Total number of SQL queries executed",
    labelnames=["operation", "table"],
)

sql_query_errors = Counter(
    "sql_query_errors_total",
    "Total number of failed SQL queries",
    labelnames=["operation", "table"],
)


def _parse_operation(statement: str) -> str:
    match = _OPERATION_RE.match(statement)
    if match:
        op = match.group(1).upper()
        return "SELECT" if op == "WITH" else op
    return "OTHER"


def _parse_table(statement: str) -> str:
    match = _TABLE_RE.search(statement)
    return match.group(1).strip("\"'") if match else "unknown"


def register_query_metrics(engine: Engine) -> None:
    """Attach SQLAlchemy core event listeners to track query metrics."""

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        conn.info["query_start_time"] = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        elapsed = time.perf_counter() - conn.info.pop("query_start_time", 0)
        operation = _parse_operation(statement)
        table = _parse_table(statement)
        sql_query_duration.labels(operation=operation, table=table).observe(elapsed)
        sql_query_total.labels(operation=operation, table=table).inc()
        logger.info(
            "sql_query operation={op} table={tbl} duration={dur:.6f}s query={q}",
            op=operation,
            tbl=table,
            dur=elapsed,
            q=statement.replace("\n", " ").strip(),
        )

    @event.listens_for(engine, "handle_error")
    def _handle_error(exception_context):
        statement = exception_context.statement or ""
        operation = _parse_operation(statement)
        table = _parse_table(statement)
        sql_query_errors.labels(operation=operation, table=table).inc()
        logger.error(
            "sql_query_error operation={op} table={tbl} error={err} query={q}",
            op=operation,
            tbl=table,
            err=str(exception_context.original_exception),
            q=statement.replace("\n", " ").strip(),
        )
