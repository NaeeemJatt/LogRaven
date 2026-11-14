"""Volatile Field Stripper for Cloud Configuration Dictionaries (FR-MOD2-03, TC-MOD2-001).

Removes transient API metadata, request IDs, pagination tokens, and etags that cause false-positive configuration drift alerts.
"""

from typing import Any, Dict, List, Union

# Set of lowercase field names to strip from configurations
VOLATILE_KEYS = {
    "responsemetadata",
    "requestid",
    "httpstatuscode",
    "httpheaders",
    "retryattempts",
    "hostid",
    "extendedrequestid",
    "date",
    "etag",
    "lastevaluatedtime",
    "nexttoken",
    "marker",
    "continuationtoken",
    "generation",
    "metadatageneration",
}


def strip_volatile_fields(data: Any) -> Any:
    """Recursively removes transient and volatile fields from cloud configurations."""
    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            if str(k).lower() in VOLATILE_KEYS:
                continue
            cleaned[k] = strip_volatile_fields(v)
        return cleaned

    elif isinstance(data, list):
        return [strip_volatile_fields(item) for item in data]

    elif isinstance(data, tuple):
        return tuple(strip_volatile_fields(item) for item in data)

    return data

