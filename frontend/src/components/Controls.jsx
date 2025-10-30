import React, { useState, useEffect } from 'react'

const Controls = ({ 
  deviceConnected, 
  streaming, 
  deviceInfo, 
  onStartStreaming, 
  onStopStreaming, 
  onUpdateSettings 
}) => {
  const [frequency, setFrequency] = useState(100000000) // 100 MHz
  const [gain, setGain] = useState('auto')
  const [sampleRate, setSampleRate] = useState(2048000) // 2.048 MS/s
  const [bandwidth, setBandwidth] = useState('')
  // gainValue no longer used; control gain via select only

  useEffect(() => {
    if (deviceInfo) {
      setFrequency(deviceInfo.frequency || 100000000)
      setGain(deviceInfo.gain || 'auto')
      setSampleRate(deviceInfo.sample_rate || 2048000)
      setBandwidth(deviceInfo.bandwidth || '')
    }
  }, [deviceInfo])

  const handleFrequencyChange = (e) => {
    const value = parseFloat(e.target.value)
    setFrequency(value)
  }

  const handleGainChange = (e) => {
    const value = e.target.value
    setGain(value)
    // numeric gain handled as string value passed to backend
  }

  // removed unused handleGainValueChange

  const handleSampleRateChange = (e) => {
    const value = parseFloat(e.target.value)
    setSampleRate(value)
  }

  const handleBandwidthChange = (e) => {
    const value = e.target.value
    setBandwidth(value)
  }

  const applySettings = () => {
    const settings = {
      frequency,
      gain,
      sample_rate: sampleRate
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

  return (
    <div className="card">
      <h3 className="text-lg font-bold mb-4">Controls</h3>
      
      {!deviceConnected ? (
        <p className="text-gray-300">Connect a device to access controls</p>
      ) : (
        <div className="space-y-4">
          {/* Frequency Control */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Frequency: {formatFrequency(frequency)}
            </label>
            <input
              type="range"
              min="25000000"
              max="1750000000"
              step="1000000"
              value={frequency}
              onChange={handleFrequencyChange}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>25 MHz</span>
              <span>1.75 GHz</span>
            </div>
          </div>

          {/* Gain Control */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">Gain</label>
            <select
              value={gain}
              onChange={handleGainChange}
              className="input w-full"
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

          {/* Sample Rate Control */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Sample Rate: {formatSampleRate(sampleRate)}
            </label>
            <select
              value={sampleRate}
              onChange={handleSampleRateChange}
              className="input w-full"
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

          {/* Bandwidth Control */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">Bandwidth (Optional)</label>
            <input
              type="number"
              value={bandwidth}
              onChange={handleBandwidthChange}
              placeholder="Auto"
              className="input w-full"
            />
          </div>

          {/* Apply Settings Button */}
          <button
            className="btn btn-primary w-full"
            onClick={applySettings}
          >
            Apply Settings
          </button>

          {/* Streaming Controls */}
          <div className="border-t border-gray-600 pt-4">
            <h4 className="text-sm font-bold text-gray-300 mb-2">Streaming</h4>
            
            {!streaming ? (
              <button
                className="btn btn-success w-full"
                onClick={onStartStreaming}
              >
                Start Streaming
              </button>
            ) : (
              <button
                className="btn btn-danger w-full"
                onClick={onStopStreaming}
              >
                Stop Streaming
              </button>
            )}
          </div>

          {/* Presets */}
          <div className="border-t border-gray-600 pt-4">
            <h4 className="text-sm font-bold text-gray-300 mb-2">Quick Presets</h4>
            
            <div className="grid grid-cols-2 gap-2">
              <button
                className="btn btn-secondary text-xs"
                onClick={() => {
                  setFrequency(87500000) // FM Radio
                  setGain('auto')
                  setSampleRate(2048000)
                }}
              >
                FM Radio
              </button>
              
              <button
                className="btn btn-secondary text-xs"
                onClick={() => {
                  setFrequency(118000000) // Aviation
                  setGain('auto')
                  setSampleRate(2048000)
                }}
              >
                Aviation
              </button>
              
              <button
                className="btn btn-secondary text-xs"
                onClick={() => {
                  setFrequency(144000000) // 2m Ham
                  setGain('auto')
                  setSampleRate(2048000)
                }}
              >
                2m Ham
              </button>
              
              <button
                className="btn btn-secondary text-xs"
                onClick={() => {
                  setFrequency(430000000) // 70cm Ham
                  setGain('auto')
                  setSampleRate(2048000)
                }}
              >
                70cm Ham
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Controls


