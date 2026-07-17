from sqlalchemy.exc import OperationalError

from app.services.schema_bootstrap import _is_retryable_schema_error


def _operational_error(errno: int) -> OperationalError:
    return OperationalError("stmt", {}, Exception(errno, "mysql error"))


def test_retryable_schema_error_includes_concurrent_ddl():
    assert _is_retryable_schema_error(_operational_error(1684)) is True


def test_retryable_schema_error_includes_lock_wait_timeout():
    assert _is_retryable_schema_error(_operational_error(1205)) is True


def test_retryable_schema_error_ignores_unknown_codes():
    assert _is_retryable_schema_error(_operational_error(1062)) is False
