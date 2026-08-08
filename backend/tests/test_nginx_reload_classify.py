from app.services.nginx_conf import classify_reload_error


def test_classify_reload_error_certificate():
    stderr = (
        'nginx: [emerg] cannot load certificate "/data/engine/certs/2/fullchain.pem": '
        "PEM_read_bio_X509() failed (SSL: error:0D07209B:asn1 encoding routines)"
    )
    assert classify_reload_error(stderr) == "certificate"


def test_classify_reload_error_engine():
    assert classify_reload_error("openresty: invalid option") == "engine"
    assert classify_reload_error("") == "engine"
