# LogRaven — user-facing strings and stable warning codes (no vendor names in UI).

# API / UI warning codes (machine-stable)
DECODER_MANAGER_UNAVAILABLE = "DECODER_MANAGER_UNAVAILABLE"
DECODERS_NOT_APPLICABLE = "DECODERS_NOT_APPLICABLE"
FALLBACK_TO_PARSERS = "FALLBACK_TO_PARSERS"
FALLBACK_TO_DECODERS = "FALLBACK_TO_DECODERS"

USER_MESSAGES: dict[str, str] = {
    DECODER_MANAGER_UNAVAILABLE: (
        "Decoder manager is not running or unreachable. Results were produced using parsers instead."
    ),
    DECODERS_NOT_APPLICABLE: (
        "Decoders are not applicable for this file type; parsers were used instead."
    ),
    FALLBACK_TO_PARSERS: (
        "Decoders could not process this file; parsers were used instead."
    ),
    FALLBACK_TO_DECODERS: (
        "Parsers could not read this file; decoders were used instead."
    ),
}


def user_message(code: str) -> str:
    return USER_MESSAGES.get(code, "Processing path was adjusted; see details on the file.")
