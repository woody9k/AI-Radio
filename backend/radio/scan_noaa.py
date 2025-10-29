from typing import List, Dict, Any
import numpy as np

from backend.config.bands import NOAA_CHANNELS


def scan_noaa(read_spectrum_fn, threshold_db: float = 6.0) -> List[Dict[str, Any]]:
	"""Scan NOAA weather radio channels and return strongest candidates."""
	results = []
	for ch in NOAA_CHANNELS:
		freqs, spectrum_db = read_spectrum_fn(ch)
		if freqs is None or spectrum_db is None:
			continue
		peak = float(np.max(spectrum_db))
		median = float(np.median(spectrum_db))
		snr = peak - median
		if snr >= threshold_db:
			results.append({
				'frequency': ch,
				'snr_db': snr,
				'modulation': 'NFM',
				'description': 'NOAA Weather'
			})

	return sorted(results, key=lambda r: -r['snr_db'])


