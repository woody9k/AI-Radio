// deviceCapabilities.js

// Known device catalogs (approximate practical ranges)
const DEVICE_CATALOG = {
  RTL_SDR: { minHz: 24e6, maxHz: 1.766e9 },
  HACKRF_ONE: { minHz: 1e6, maxHz: 6e9 },
};

function identifyFromInfo(deviceInfo = {}) {
  const caps = deviceInfo.capabilities || {};
  const type = (caps.device_type || '').toLowerCase();
  const idStr = JSON.stringify(deviceInfo).toLowerCase();

  if (type.includes('rtl') || idStr.includes('rtl') || idStr.includes('rtlsdr')) {
    return 'RTL_SDR';
  }
  if (type.includes('hackrf') || idStr.includes('hackrf')) {
    return 'HACKRF_ONE';
  }
  return null;
}

export function getDeviceCaps(deviceInfo) {
  const detected = identifyFromInfo(deviceInfo);
  if (detected && DEVICE_CATALOG[detected]) {
    return { ...DEVICE_CATALOG[detected], source: detected };
  }
  // Fallback to any explicit caps provided by backend
  const caps = (deviceInfo && deviceInfo.capabilities) || {};
  if (typeof caps.min_hz === 'number' && typeof caps.max_hz === 'number') {
    return { minHz: caps.min_hz, maxHz: caps.max_hz, source: 'backend' };
  }
  // Conservative default
  return { minHz: 24e6, maxHz: 1.766e9, source: 'default' };
}

export function getBrowsableRange(deviceInfo) {
  const { minHz, maxHz } = getDeviceCaps(deviceInfo);
  const pad = 500e6;
  const low = Math.max(0, minHz - pad);
  const high = maxHz + pad;
  return { minHz: low, maxHz: high };
}

export function clampFrequency(freqHz, deviceInfo) {
  const { minHz, maxHz } = getBrowsableRange(deviceInfo);
  if (freqHz < minHz) return minHz;
  if (freqHz > maxHz) return maxHz;
  return freqHz;
}
