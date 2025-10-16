import React, { useState, useEffect } from 'react'

const AIPanel = ({ detections, streaming, viewMode = 'beginner', onListenToSignal }) => {
  const [anomalies, setAnomalies] = useState([])
  const [signalTypes, setSignalTypes] = useState([])
  const [aiEnabled, setAiEnabled] = useState(false)

  useEffect(() => {
    // Process detections for anomalies and signal types
    if (detections.length > 0) {
      const latestDetection = detections[0]
      
      // Simple anomaly detection based on signal strength
      if (latestDetection.power > -50) {
        const anomaly = {
          ...latestDetection,
          type: 'high_power_signal',
          severity: latestDetection.power > -30 ? 'high' : 'medium'
        }
        
        setAnomalies(prev => [anomaly, ...prev].slice(0, 20))
      }

      // Classify signal types based on frequency and characteristics
      const signalType = classifySignal(latestDetection)
      if (signalType) {
        setSignalTypes(prev => {
          const existing = prev.find(s => s.frequency === latestDetection.frequency)
          if (existing) {
            return prev.map(s => 
              s.frequency === latestDetection.frequency 
                ? { ...s, ...signalType, lastSeen: latestDetection.timestamp }
                : s
            )
          } else {
            return [{ ...signalType, ...latestDetection }, ...prev].slice(0, 20)
          }
        })
      }
    }
  }, [detections])

  const classifySignal = (signal) => {
    // Use backend classification if available
    if (signal.category && signal.description) {
      return {
        type: signal.description,
        confidence: signal.confidence || 0.5,
        description: viewMode === 'beginner' 
          ? signal.description 
          : `${signal.description} | ${signal.modulation || 'Unknown'} | ${formatFrequency(signal.frequency)} | BW: ${signal.bandwidth ? (signal.bandwidth/1000).toFixed(1) + 'kHz' : 'Unknown'} | SNR: ${signal.snr ? signal.snr.toFixed(1) + 'dB' : 'Unknown'}`,
        category: signal.category,
        modulation: signal.modulation,
        technical: signal.technical_details
      }
    }

    // Fallback to frontend classification
    const freq = signal.frequency
    const power = signal.power
    const bandwidth = signal.bandwidth || 0

    // FM Broadcast (88-108 MHz)
    if (freq >= 88e6 && freq <= 108e6) {
      return {
        type: 'FM Broadcast Radio',
        confidence: 0.9,
        description: viewMode === 'beginner' 
          ? 'Commercial FM radio station'
          : `FM Broadcast | FM | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // Aviation (118-137 MHz)
    if (freq >= 118e6 && freq <= 137e6) {
      return {
        type: 'Aviation Communication',
        confidence: 0.8,
        description: viewMode === 'beginner' 
          ? 'Aircraft communication'
          : `Aviation | AM | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // 2m Ham Radio (144-148 MHz)
    if (freq >= 144e6 && freq <= 148e6) {
      return {
        type: '2m Ham Radio',
        confidence: 0.7,
        description: viewMode === 'beginner' 
          ? 'Amateur radio 2m band'
          : `2m Ham | FM/SSB | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // 70cm Ham Radio (430-450 MHz)
    if (freq >= 430e6 && freq <= 450e6) {
      return {
        type: '70cm Ham Radio',
        confidence: 0.7,
        description: viewMode === 'beginner' 
          ? 'Amateur radio 70cm band'
          : `70cm Ham | FM | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // Weather Radio (162.4-162.55 MHz)
    if (freq >= 162.4e6 && freq <= 162.55e6) {
      return {
        type: 'NOAA Weather Radio',
        confidence: 0.8,
        description: viewMode === 'beginner' 
          ? 'NOAA weather radio'
          : `Weather | FM | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // CB Radio (26.965-27.405 MHz)
    if (freq >= 26.965e6 && freq <= 27.405e6) {
      return {
        type: 'CB Radio',
        confidence: 0.7,
        description: viewMode === 'beginner' 
          ? 'CB radio communication'
          : `CB Radio | AM/SSB | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // Digital signals (high bandwidth, low power)
    if (bandwidth > 100000 && power < -60) {
      return {
        type: 'Digital Signal',
        confidence: 0.5,
        description: viewMode === 'beginner' 
          ? 'Unknown digital transmission'
          : `Digital | Unknown | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    // Strong narrowband signal
    if (bandwidth < 10000 && power > -40) {
      return {
        type: 'Narrowband Signal',
        confidence: 0.4,
        description: viewMode === 'beginner' 
          ? 'Strong narrowband transmission'
          : `Narrowband | Unknown | ${formatFrequency(freq)} | BW: ${(bandwidth/1000).toFixed(1)}kHz | SNR: ${power.toFixed(1)}dB`
      }
    }

    return null
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

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'text-red-400'
      case 'medium': return 'text-yellow-400'
      case 'low': return 'text-green-400'
      default: return 'text-gray-400'
    }
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-400'
    if (confidence >= 0.6) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">AI Analysis</h3>
        <div className="flex items-center gap-2">
          <span className={`status ${aiEnabled ? 'status-streaming' : 'status-disconnected'}`}>
            {aiEnabled ? 'Active' : 'Inactive'}
          </span>
          <button
            className={`btn ${aiEnabled ? 'btn-danger' : 'btn-success'} text-xs`}
            onClick={() => setAiEnabled(!aiEnabled)}
          >
            {aiEnabled ? 'Disable' : 'Enable'}
          </button>
        </div>
      </div>

      {!streaming ? (
        <p className="text-gray-300 text-sm">Start streaming to see AI analysis</p>
      ) : (
        <div className="space-y-4">
          {/* Anomalies */}
          <div>
            <h4 className="text-sm font-bold text-gray-300 mb-2">
              Anomalies ({anomalies.length})
            </h4>
            
            {anomalies.length === 0 ? (
              <p className="text-gray-400 text-xs">No anomalies detected</p>
            ) : (
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {anomalies.slice(0, 5).map((anomaly, index) => (
                  <div key={index} className="bg-gray-800 p-2 rounded text-xs">
                    <div className="flex justify-between items-center">
                      <span className={getSeverityColor(anomaly.severity)}>
                        {anomaly.type.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="text-gray-400">
                        {formatFrequency(anomaly.frequency)}
                      </span>
                    </div>
                    <div className="text-gray-300">
                      Power: {anomaly.power.toFixed(1)} dB
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Signal Types */}
          <div>
            <h4 className="text-sm font-bold text-gray-300 mb-2">
              Signal Types ({signalTypes.length})
            </h4>
            
            {signalTypes.length === 0 ? (
              <p className="text-gray-400 text-xs">No signals classified</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {signalTypes.slice(0, 10).map((signal, index) => (
                  <div key={index} className="bg-gray-800 p-2 rounded text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">
                          {signal.type}
                        </span>
                        {onListenToSignal && (
                          <button
                            className="btn btn-primary"
                            style={{ fontSize: '10px', padding: '2px 6px' }}
                            onClick={() => onListenToSignal(signal)}
                            title="Listen to this signal"
                          >
                            🔊
                          </button>
                        )}
                      </div>
                      <span className={getConfidenceColor(signal.confidence)}>
                        {(signal.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    
                    <div className="text-gray-300 mb-1">
                      {formatFrequency(signal.frequency)}
                    </div>
                    
                    <div className="text-gray-400 text-xs">
                      {signal.description}
                    </div>
                    
                    {signal.lastSeen && (
                      <div className="text-gray-500 text-xs mt-1">
                        Last seen: {new Date(signal.lastSeen).toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Statistics */}
          <div className="border-t border-gray-600 pt-4">
            <h4 className="text-sm font-bold text-gray-300 mb-2">Statistics</h4>
            
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-800 p-2 rounded">
                <div className="text-gray-400">Total Signals</div>
                <div className="text-white font-bold">{detections.length}</div>
              </div>
              
              <div className="bg-gray-800 p-2 rounded">
                <div className="text-gray-400">Anomalies</div>
                <div className="text-white font-bold">{anomalies.length}</div>
              </div>
              
              <div className="bg-gray-800 p-2 rounded">
                <div className="text-gray-400">Classified</div>
                <div className="text-white font-bold">{signalTypes.length}</div>
              </div>
              
              <div className="bg-gray-800 p-2 rounded">
                <div className="text-gray-400">Avg Confidence</div>
                <div className="text-white font-bold">
                  {signalTypes.length > 0 
                    ? ((signalTypes.reduce((sum, s) => sum + s.confidence, 0) / signalTypes.length) * 100).toFixed(0)
                    : 0}%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AIPanel


