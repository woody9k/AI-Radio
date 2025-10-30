import React, { useState, useEffect, useMemo } from 'react'
import { getDeviceCaps } from '../api/deviceCapabilities'

const Controls = ({ 
  deviceConnected, 
  streaming, 
  deviceInfo, 
  onStartStreaming, 
  onStopStreaming, 
  onUpdateSettings 
}) => {
  const [frequency, setFrequency] = useState(100000000) // 100 MHz
  const [mode, setMode] = useState('WFM')
  const [gain, setGain] = useState('auto')
  const [sampleRate, setSampleRate] = useState(2048000) // 2.048 MS/s
  const [bandwidth, setBandwidth] = useState('')
  const [agcEnabled, setAgcEnabled] = useState(false)
  const [squelchEnabled, setSquelchEnabled] = useState(false)
  const [squelchThreshold, setSquelchThreshold] = useState(-120)
  const [biasT, setBiasT] = useState(false)

  useEffect(() => {
    if (deviceInfo) {
      setFrequency(deviceInfo.frequency || 100000000)
      setMode(deviceInfo.mode || 'WFM')
      setGain(deviceInfo.gain || 'auto')
      setSampleRate(deviceInfo.sample_rate || 2048000)
      setBandwidth(deviceInfo.bandwidth || '')
      setAgcEnabled(deviceInfo.agc_enabled || false)
      setBiasT(deviceInfo.bias_t || false)
      // Squelch info might not be in deviceInfo, it's in audio demodulator
    }
  }, [deviceInfo])

  const deviceCaps = useMemo(() => getDeviceCaps(deviceInfo || {}), [deviceInfo])

  // Frequency is now adjusted via Spectrum header controls

  // Step handlers removed

  // Removed local digit controls in favor of Spectrum header

  // Wheel digit handler removed

  const handleModeChange = (e) => {
    setMode(e.target.value)
  }

  const handleGainChange = (e) => {
    const value = e.target.value
    setGain(value)
  }

  const handleSampleRateChange = (e) => {
    const value = parseFloat(e.target.value)
    setSampleRate(value)
  }

  const handleBandwidthChange = (e) => {
    const value = e.target.value
    setBandwidth(value)
  }

  const handleAgcToggle = (e) => {
    setAgcEnabled(e.target.checked)
  }

  const handleSquelchToggle = (e) => {
    setSquelchEnabled(e.target.checked)
  }

  const handleSquelchThresholdChange = (e) => {
    setSquelchThreshold(parseFloat(e.target.value))
  }

  const handleBiasTToggle = (e) => {
    setBiasT(e.target.checked)
  }

  const applySettings = () => {
    const settings = {
      frequency,
      mode,
      gain,
      sample_rate: sampleRate,
      agc_enabled: agcEnabled,
      squelch_enabled: squelchEnabled,
      squelch_threshold: squelchThreshold,
      bias_t: biasT
    }
    
    if (bandwidth) {
      settings.bandwidth = parseFloat(bandwidth)
    }
    
    onUpdateSettings(settings)
  }

  const formatFrequency = (freq) => {
    if (freq >= 1e9) {
      return `${(freq / 1e9).toFixed(3)} GHz`
    } else if (freq >= 1e6) {
      return `${(freq / 1e6).toFixed(3)} MHz`
    } else if (freq >= 1e3) {
      return `${(freq / 1e3).toFixed(3)} kHz`
    } else {
      return `${freq.toFixed(0)} Hz`
    }
  }

  const formatSampleRate = (rate) => {
    return `${(rate / 1e6).toFixed(3)} MS/s`
  }

  const deviceSupportsBiasT = deviceInfo?.capabilities?.bias_t || false

  return (
    <div className="card" style={{ padding: '8px', width: '100%', boxSizing: 'border-box' }}>
      <h3 className="text-lg font-bold mb-4">Controls</h3>
      
      <div>
        {!deviceConnected && (
          <p className="text-gray-300 text-sm" style={{ marginBottom: 8 }}>
            Connect a device to enable controls (preview shown)
          </p>
        )}
        <fieldset disabled={!deviceConnected} style={{ border: 0, padding: 0, margin: 0, opacity: deviceConnected ? 1 : 0.6 }}>
          {/* Radio Section */}
          <div style={{ background: '#151515', border: '1px solid #333', borderRadius: 6, padding: 8, marginBottom: 6 }}>
            <div className="text-xs uppercase tracking-wide text-gray-300 font-semibold" style={{ marginBottom: 6 }}>
              Radio Controls
            </div>

            {/* Frequency section now controlled from Spectrum header; show info only */}
            <div className="mb-3">
              <label className="block text-sm text-gray-300 mb-1">
                Frequency: {formatFrequency(frequency)} (range {formatFrequency(deviceCaps.minHz)} - {formatFrequency(deviceCaps.maxHz)})
              </label>
            </div>

            {/* Mode + Bandwidth */}
            <div className="mb-3" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Mode</label>
                <select
                  value={mode}
                  onChange={handleModeChange}
                  className="input w-full"
                  style={{ padding: '4px 6px', fontSize: '12px' }}
                >
                  <option value="WFM">WFM</option>
                  <option value="NFM">NFM</option>
                  <option value="AM">AM</option>
                  <option value="SSB">SSB</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Filter/Bandwidth</label>
                <input
                  type="number"
                  value={bandwidth}
                  onChange={handleBandwidthChange}
                  placeholder="Auto"
                  className="input w-full"
                  style={{ padding: '4px 6px', fontSize: '12px' }}
                />
              </div>
            </div>

            {/* Squelch + AGC */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '8px' }}>
              <label className="text-sm text-gray-300 flex items-center gap-2 cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={squelchEnabled}
                  onChange={handleSquelchToggle}
                  style={{ cursor: 'pointer' }}
                /> 
                Squelch
              </label>
              <label className="text-sm text-gray-300 flex items-center gap-2 cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={agcEnabled}
                  onChange={handleAgcToggle}
                  style={{ cursor: 'pointer' }}
                /> 
                AGC
              </label>
            </div>

            {squelchEnabled && (
              <div className="mb-3">
                <label className="block text-sm text-gray-300 mb-1">
                  Squelch Threshold: {squelchThreshold.toFixed(0)} dB
                </label>
                <input
                  type="range"
                  min="-140"
                  max="-80"
                  step="1"
                  value={squelchThreshold}
                  onChange={handleSquelchThresholdChange}
                  className="w-full"
                />
              </div>
            )}

            <button 
              className="btn btn-primary w-full" 
              onClick={applySettings}
              style={{ marginTop: '6px', padding: '6px' }}
            >
              Apply Settings
            </button>
          </div>

          {/* Device Section */}
          <div style={{ background: '#151515', border: '1px solid #333', borderRadius: 6, padding: 8, marginBottom: 6 }}>
            <div className="text-xs uppercase tracking-wide text-gray-300 font-semibold" style={{ marginBottom: 6 }}>
              Device Settings
            </div>

            {/* Gain */}
            <div className="mb-3">
              <label className="block text-sm text-gray-300 mb-1">Gain</label>
              <select
                value={gain}
                onChange={handleGainChange}
                className="input w-full"
                style={{ padding: '4px 6px', fontSize: '12px' }}
              >
                <option value="auto">Auto</option>
                <option value="0">0 dB</option>
                <option value="9.9">9.9 dB</option>
                <option value="14.4">14.4 dB</option>
                <option value="19.7">19.7 dB</option>
                <option value="24.3">24.3 dB</option>
                <option value="29.7">29.7 dB</option>
                <option value="34.8">34.8 dB</option>
                <option value="42.1">42.1 dB</option>
                <option value="43.9">43.9 dB</option>
              </select>
            </div>

            {/* Sample rate */}
            <div className="mb-3">
              <label className="block text-sm text-gray-300 mb-1">
                Sample Rate: {formatSampleRate(sampleRate)}
              </label>
              <select
                value={sampleRate}
                onChange={handleSampleRateChange}
                className="input w-full"
                style={{ padding: '4px 6px', fontSize: '12px' }}
              >
                <option value={250000}>250 kS/s</option>
                <option value={500000}>500 kS/s</option>
                <option value={1024000}>1.024 MS/s</option>
                <option value={1536000}>1.536 MS/s</option>
                <option value={2048000}>2.048 MS/s</option>
                <option value={2560000}>2.56 MS/s</option>
                <option value={3072000}>3.072 MS/s</option>
              </select>
            </div>

            {/* Bias-T (if supported) */}
            {deviceSupportsBiasT && (
              <label className="text-sm text-gray-300 flex items-center gap-2 cursor-pointer mb-2">
                <input 
                  type="checkbox" 
                  checked={biasT}
                  onChange={handleBiasTToggle}
                  style={{ cursor: 'pointer' }}
                /> 
                Bias-T
              </label>
            )}

            {/* Streaming */}
            <div className="border-t border-gray-600 pt-4" style={{ marginTop: '10px' }}>
              <h4 className="text-sm font-bold text-gray-300 mb-1">Streaming</h4>
              {!streaming ? (
                <button 
                  className="btn btn-success w-full" 
                  onClick={onStartStreaming}
                  style={{ padding: '6px' }}
                >
                  Start Streaming
                </button>
              ) : (
                <button 
                  className="btn btn-danger w-full" 
                  onClick={onStopStreaming}
                  style={{ padding: '6px' }}
                >
                  Stop Streaming
                </button>
              )}
            </div>
          </div>
        </fieldset>
      </div>
    </div>
  )
}

// Local DigitGroup removed; stepper moved to Spectrum header

export default Controls
