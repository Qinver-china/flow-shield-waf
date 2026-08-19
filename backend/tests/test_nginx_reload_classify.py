from app.services.nginx_conf import (
    EngineReloadResult,
    classify_reload_error,
    format_reload_warn_message,
)


def test_classify_reload_error_certificate():
    stderr = (
        'nginx: [emerg] cannot load certificate "/data/engine/certs/2/fullchain.pem": '
        "PEM_read_bio_X509() failed (SSL: error:0D07209B:asn1 encoding routines)"
    )
    assert classify_reload_error(stderr) == "certificate"


def test_classify_reload_error_engine():
    assert classify_reload_error("openresty: invalid option") == "engine"
    assert classify_reload_error("") == "engine"


def test_format_reload_warn_includes_certificate_detail():
    result = EngineReloadResult(
        ok=False,
        reason="certificate",
        detail='cannot load certificate "/data/engine/certs/2/fullchain.pem"',
    )
    msg = format_reload_warn_message(result)
    assert "证书异常" in msg
    assert "fullchain.pem" in msg


def test_format_reload_warn_includes_engine_detail():
    result = EngineReloadResult(
        ok=False,
        reason="engine",
        detail="bind() to 0.0.0.0:80 failed (98: Address already in use)",
    )
    msg = format_reload_warn_message(result)
    assert "引擎配置重载失败" in msg
    assert "Address already in use" in msg


def test_format_reload_warn_fallback_without_detail():
    result = EngineReloadResult(ok=False, reason="engine")
    msg = format_reload_warn_message(result)
    assert "请检查引擎状态" in msg


def test_engine_is_running_missing_pid(tmp_path, monkeypatch):
    from app.services import nginx_conf

    monkeypatch.setattr(nginx_conf, "ENGINE_PID_PATH", str(tmp_path / "nginx.pid"))
    assert nginx_conf._engine_is_running() is False


def test_engine_is_running_stale_pid(tmp_path, monkeypatch):
    from app.services import nginx_conf

    pid_path = tmp_path / "nginx.pid"
    pid_path.write_text("999999999\n", encoding="utf-8")
    monkeypatch.setattr(nginx_conf, "ENGINE_PID_PATH", str(pid_path))
    assert nginx_conf._engine_is_running() is False


def test_engine_is_running_alive(tmp_path, monkeypatch):
    import os

    from app.services import nginx_conf

    pid_path = tmp_path / "nginx.pid"
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    monkeypatch.setattr(nginx_conf, "ENGINE_PID_PATH", str(pid_path))
    assert nginx_conf._engine_is_running() is True
