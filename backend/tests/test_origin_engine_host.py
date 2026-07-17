from app.services.origin import build_upstream_url, resolve_origin_host_for_engine


def test_resolve_docker_internal_to_gateway(monkeypatch):
    monkeypatch.setenv("WAF_ORIGIN_HOST_GATEWAY", "172.17.0.1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert resolve_origin_host_for_engine("host.docker.internal") == "172.17.0.1"
    get_settings.cache_clear()


def test_build_upstream_url_rewrites_docker_alias(monkeypatch):
    monkeypatch.setenv("WAF_ORIGIN_HOST_GATEWAY", "172.17.0.1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert build_upstream_url("host.docker.internal", "http", 8088) == "http://172.17.0.1:8088"
    get_settings.cache_clear()
