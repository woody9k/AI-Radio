from typing import List, Dict, Any, Tuple
import numpy as np

from backend.config.bands import FM_BAND


def scan_fm_band(read_spectrum_fn, center_step_hz: float = 1.0e6,
				 dwell_ms: int = 200, threshold_db: float = 12.0) -> List[Dict[str, Any]]:
	"""Coarse FM band scan using provided spectrum reader.

	read_spectrum_fn(center_freq_hz) must tune the device, dwell briefly,
	and return (freqs_array_hz, spectrum_db_array).
	"""
	start_hz, end_hz = FM_BAND
	centers: List[float] = []
	cf = start_hz + center_step_hz / 2
	while cf < end_hz:
		centers.append(cf)
		cf += center_step_hz

	candidates: List[Tuple[float, float]] = []  # (freq_hz, peak_db)
	for cf in centers:
		freqs, spectrum_db = read_spectrum_fn(cf)
		if freqs is None or spectrum_db is None:
			continue
		peak_idx = int(np.argmax(spectrum_db))
		peak_db = float(spectrum_db[peak_idx])
		if peak_db - float(np.median(spectrum_db)) >= threshold_db:
			candidates.append((float(freqs[peak_idx]), peak_db))

	# Deduplicate nearby peaks into stations by 200 kHz bins
	stations: List[Dict[str, Any]] = []
	seen_bins = set()
	for freq_hz, peak_db in sorted(candidates, key=lambda x: -x[1]):
		bin_key = int(round(freq_hz / 200000.0))
		if bin_key in seen_bins:
			continue
		seen_bins.add(bin_key)
		stations.append({
			'frequency': freq_hz,
			'snr_db': peak_db,
			'modulation': 'WFM',
			'description': 'FM Broadcast candidate'
		})

	return stations[:30]


