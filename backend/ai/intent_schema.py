from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator


class IntentBase(BaseModel):
	intent: str
	params: Dict[str, Any] = Field(default_factory=dict)
	meta: Optional[Dict[str, Any]] = None


class TuneParams(BaseModel):
	frequency_hz: float
	mode: Optional[Literal['WFM', 'NFM', 'AM', 'SSB']] = None
	bandwidth_hz: Optional[float] = None

	@validator('frequency_hz')
	def freq_bounds(cls, v: float) -> float:
		if not (24e6 <= v <= 1766e6):
			raise ValueError('frequency out of RTL-SDR bounds')
		return v


class ScanParams(BaseModel):
	band: Literal['fm', 'noaa', 'aviation', 'ham_2m', 'ham_70cm', 'custom']
	strategy: Optional[Literal['peak_sweep', 'coarse_fine']] = 'peak_sweep'
	dwell_ms: Optional[int] = 200
	threshold_db: Optional[float] = 12.0


class WeatherTuneParams(BaseModel):
	region: Optional[str] = 'auto'


class HydrogenParams(BaseModel):
	integrate_sec: Optional[int] = 30


class MeteorParams(BaseModel):
	center_hz: Optional[float] = None
	span_hz: Optional[float] = 2e6
	log: Optional[bool] = True


class IntentParseResult(BaseModel):
	intent: Literal[
		'TUNE', 'SCAN', 'WEATHER_TUNE', 'HYDROGEN_LINE_TUNE',
		'METEOR_LISTEN', 'PRESET', 'STATUS', 'QUERY_STATIONS', 'HELP'
	]
	params: Dict[str, Any] = Field(default_factory=dict)
	meta: Optional[Dict[str, Any]] = None
	explanation: Optional[str] = None


