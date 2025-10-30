from typing import Any, Literal

from pydantic import BaseModel, Field, validator


class IntentBase(BaseModel):
    intent: str
    params: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] | None = None


class TuneParams(BaseModel):
    frequency_hz: float
    mode: Literal["WFM", "NFM", "AM", "SSB"] | None = None
    bandwidth_hz: float | None = None

    @validator("frequency_hz")
    def freq_bounds(cls, v: float) -> float:
        if not (24e6 <= v <= 1766e6):
            raise ValueError("frequency out of RTL-SDR bounds")
        return v


class ScanParams(BaseModel):
    band: Literal["fm", "noaa", "aviation", "ham_2m", "ham_70cm", "custom"]
    strategy: Literal["peak_sweep", "coarse_fine"] | None = "peak_sweep"
    dwell_ms: int | None = 200
    threshold_db: float | None = 12.0


class WeatherTuneParams(BaseModel):
    region: str | None = "auto"


class HydrogenParams(BaseModel):
    integrate_sec: int | None = 30


class MeteorParams(BaseModel):
    center_hz: float | None = None
    span_hz: float | None = 2e6
    log: bool | None = True


class IntentParseResult(BaseModel):
    intent: Literal[
        "TUNE",
        "SCAN",
        "WEATHER_TUNE",
        "HYDROGEN_LINE_TUNE",
        "METEOR_LISTEN",
        "PRESET",
        "STATUS",
        "QUERY_STATIONS",
        "HELP",
    ]
    params: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] | None = None
    explanation: str | None = None
