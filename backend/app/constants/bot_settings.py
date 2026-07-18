"""Bot library constants."""

RESERVED_CATEGORY_OTHER = "other"
DEFAULT_CATEGORY = RESERVED_CATEGORY_OTHER

# Slug values that cannot be created via the category API.
RESERVED_CATEGORY_VALUES = frozenset({RESERVED_CATEGORY_OTHER})
