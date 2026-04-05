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


class PlayDecoderSummary(BaseModel):
    ok: bool
    manager_reachable: bool
    event_count: int = 0
    events_trimmed: bool = False
    warning_codes: list[str] = Field(default_factory=list)
    user_messages: list[str] = Field(default_factory=list)
    error: str | None = None
    sample_events: list[PlayParserSampleEvent] | None = None


class PlayParserCompareMetrics(BaseModel):
    native_event_count: int
    decoder_event_count: int
    count_delta: int
    sample_pairs_compared: int
    timestamp_agreement_ratio: float
    source_ip_agreement_ratio: float


class PlayParserEvaluateCompareResponse(BaseModel):
    parser_results: list[PlayParserEvaluateItem]
    decoders: PlayDecoderSummary
    compare: PlayParserCompareMetrics | None = None
