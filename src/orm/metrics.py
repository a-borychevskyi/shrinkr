import re
import time

import structlog
from opentelemetry import metrics
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = structlog.get_logger(__name__)

_OPERATION_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b", re.IGNORECASE)
_TABLE_RE = re.compile(r"(?:FROM|INTO|UPDATE|JOIN)\s+([\"']?\w+[\"']?)", re.IGNORECASE)

meter = metrics.get_meter(__name__)

sql_query_duration = meter.create_histogram(
    name="sql.query.duration",
    description="Time spent executing SQL queries",
    unit="s",
)

sql_query_total = meter.create_counter(
    name="sql.query.count",
    description="Total number of SQL queries executed",
)

sql_query_errors = meter.create_counter(
    name="sql.query.errors",
    description="Total number of failed SQL queries",
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
        attrs = {"operation": operation, "table": table}
        sql_query_duration.record(elapsed, attributes=attrs)
        sql_query_total.add(1, attributes=attrs)

    @event.listens_for(engine, "handle_error")
    def _handle_error(exception_context):
        statement = exception_context.statement or ""
        operation = _parse_operation(statement)
        table = _parse_table(statement)
        sql_query_errors.add(1, attributes={"operation": operation, "table": table})
        logger.error(
            "sql_query_error",
            operation=operation,
            table=table,
            error=str(exception_context.original_exception),
            query=statement.replace("\n", " ").strip(),
        )
