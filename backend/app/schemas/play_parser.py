# LogRaven — PlayParser sandbox API schemas

from pydantic import BaseModel, Field


class PlayParserQuality(BaseModel):
    score: float
    valid_timestamp_ratio: float
    structured_ratio: float
    warnings: list[str] = Field(default_factory=list)


class PlayParserSampleEvent(BaseModel):
    timestamp: str | None = None
    source_type: str
    hostname: str | None = None
    username: str | None = None
    source_ip: str | None = None
    event_type: str
    event_id: str | None = None
    raw_message: str = ""
    severity_hint: str = "informational"


class PlayParserEvaluateItem(BaseModel):
    parser_key: str
    ok: bool
    event_count: int
    events_trimmed: bool = False
    quality: PlayParserQuality | None = None
    error: str | None = None
    sample_events: list[PlayParserSampleEvent] | None = None


class PlayParserEvaluateResponse(BaseModel):
    results: list[PlayParserEvaluateItem]


class PlayParserDetectCandidate(BaseModel):
    log_type: str
    confidence: float
    reasons: list[str]


class PlayParserDetectResponse(BaseModel):
    candidates: list[PlayParserDetectCandidate]
