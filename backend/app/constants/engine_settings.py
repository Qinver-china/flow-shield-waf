"""Engine proxy limits exposed in system settings."""

DEFAULT_MAX_UPLOAD_SIZE_MB = 50
MIN_MAX_UPLOAD_SIZE_MB = 1
MAX_MAX_UPLOAD_SIZE_MB = 2048

DEFAULT_ORIGIN_READ_TIMEOUT_SEC = 60
MIN_ORIGIN_READ_TIMEOUT_SEC = 5
MAX_ORIGIN_READ_TIMEOUT_SEC = 600

# Fields that require reading the request body into Lua.
BODY_READ_FIELDS = frozenset(
    {
        "http.body.raw",
        "http.body.form",
        "http.body.json",
        "derived.args_count",
    }
)
UPLOAD_FIELDS = frozenset({"http.upload.filename", "http.upload.ext"})
