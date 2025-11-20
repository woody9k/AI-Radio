import React, { useState, useEffect } from 'react'

const AdvancedScanner = () => {
  const [isScanning, setIsScanning] = useState(false)
  const [progress, setProgress] = useState(null)
  const [results, setResults] = useState([])
  const [bands, setBands] = useState([
    { start_freq: 88e6, end_freq: 108e6, step_size: 100e3, dwell_ms: 200, threshold_db: -70 }
  ])
  const [scanHistory, setScanHistory] = useState([])

  useEffect(() => {
    if (isScanning) {
      const interval = setInterval(() => {
        fetchScanStatus()
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [isScanning])

  useEffect(() => {
    fetchScanHistory()
  }, [])

  const fetchScanStatus = async () => {
    try {
      const response = await fetch('/api/scan/status')
      const data = await response.json()
      if (data.success && data.progress) {
        setProgress(data.progress)
        if (!data.progress.is_scanning) {
          setIsScanning(false)
        }
      }
    } catch (error) {
      console.error('Error fetching scan status:', error)
    }
  }

  const fetchScanHistory = async () => {
    try {
      const response = await fetch('/api/scan/history?limit=20')
      const data = await response.json()
      if (data.success) {
        setScanHistory(data.scans || [])
      }
    } catch (error) {
      console.error('Error fetching scan history:', error)
    }
  }

  const startScan = async () => {
    try {
      const response = await fetch('/api/scan/advanced', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ bands })
      })
      const data = await response.json()
      if (data.success) {
        setIsScanning(true)
        setResults([])
      } else {
        alert(`Failed to start scan: ${data.error}`)
      }
    } catch (error) {
      console.error('Error starting scan:', error)
      alert('Error starting scan')
    }
  }

  const stopScan = async () => {
    try {
      const response = await fetch('/api/scan/stop', {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        setIsScanning(false)
        if (data.results) {
          setResults(data.results)
        }
        fetchScanHistory()
      }
    } catch (error) {
      console.error('Error stopping scan:', error)
    }
  }

  const addBand = () => {
    setBands([...bands, { start_freq: 100e6, end_freq: 200e6, step_size: 100e3, dwell_ms: 200, threshold_db: -70 }])
  }

  const removeBand = (index) => {
    setBands(bands.filter((_, i) => i !== index))
  }

  const updateBand = (index, field, value) => {
    const newBands = [...bands]
    newBands[index][field] = parseFloat(value) || value
    setBands(newBands)
  }

  const formatFrequency = (freq) => {
    if (!freq) return 'N/A'
    if (freq >= 1e9) return `${(freq / 1e9).toFixed(3)} GHz`
    if (freq >= 1e6) return `${(freq / 1e6).toFixed(3)} MHz`
    if (freq >= 1e3) return `${(freq / 1e3).toFixed(1)} kHz`
    return `${freq.toFixed(0)} Hz`
  }

  return (
    <div className="advanced-scanner" style={{ padding: '12px' }}>
      <h3 style={{ marginTop: 0 }}>Advanced Scanner</h3>

      <div style={{ marginBottom: '12px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>Scan Bands</h4>
        {bands.map((band, index) => (
          <div
            key={index}
            style={{
              padding: '8px',
              background: '#1a1a1a',
              borderRadius: '4px',
              marginBottom: '8px'
            }}
          >
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
              <label style={{ fontSize: '11px', width: '80px' }}>Start (Hz)</label>
              <input
                type="number"
                value={band.start_freq}
                onChange={(e) => updateBand(index, 'start_freq', e.target.value)}
                className="input"
                style={{ width: '120px', padding: '2px 4px', fontSize: '11px' }}
              />
              <label style={{ fontSize: '11px', width: '80px' }}>End (Hz)</label>
              <input
                type="number"
                value={band.end_freq}
                onChange={(e) => updateBand(index, 'end_freq', e.target.value)}
                className="input"
                style={{ width: '120px', padding: '2px 4px', fontSize: '11px' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
              <label style={{ fontSize: '11px', width: '80px' }}>Step (Hz)</label>
              <input
                type="number"
                value={band.step_size}
                onChange={(e) => updateBand(index, 'step_size', e.target.value)}
                className="input"
                style={{ width: '120px', padding: '2px 4px', fontSize: '11px' }}
              />
              <label style={{ fontSize: '11px', width: '80px' }}>Dwell (ms)</label>
              <input
                type="number"
                value={band.dwell_ms}
                onChange={(e) => updateBand(index, 'dwell_ms', e.target.value)}
                className="input"
                style={{ width: '120px', padding: '2px 4px', fontSize: '11px' }}
              />
              <label style={{ fontSize: '11px', width: '80px' }}>Threshold (dB)</label>
              <input
                type="number"
                value={band.threshold_db}
                onChange={(e) => updateBand(index, 'threshold_db', e.target.value)}
                className="input"
                style={{ width: '120px', padding: '2px 4px', fontSize: '11px' }}
              />
              <button
                className="btn btn-secondary"
                onClick={() => removeBand(index)}
                style={{ padding: '2px 8px', fontSize: '11px', background: '#f44336' }}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
        <button className="btn btn-secondary" onClick={addBand} style={{ padding: '4px 12px', fontSize: '12px' }}>
          Add Band
        </button>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {!isScanning ? (
          <button className="btn btn-primary" onClick={startScan} style={{ flex: 1 }}>
            Start Scan
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={stopScan} style={{ flex: 1, background: '#f44336' }}>
            Stop Scan
          </button>
        )}
      </div>

      {isScanning && progress && (
        <div style={{ padding: '8px', background: '#1a1a1a', borderRadius: '4px', marginBottom: '12px', fontSize: '12px' }}>
          <div><strong>Scanning...</strong></div>
          {progress.progress !== undefined && (
            <div>
              Progress: {(progress.progress * 100).toFixed(1)}%
              <div style={{ width: '100%', height: '8px', background: '#333', borderRadius: '4px', marginTop: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${progress.progress * 100}%`, height: '100%', background: '#3b82f6', transition: 'width 0.3s' }} />
              </div>
            </div>
          )}
          {progress.current_freq && (
            <div>Current: {formatFrequency(progress.current_freq)}</div>
          )}
          <div>Signals Found: {progress.signals_found || 0}</div>
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>Scan Results ({results.length})</h4>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {results.map((result, index) => (
              <div
                key={index}
                style={{
                  padding: '8px',
                  background: '#1a1a1a',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  fontSize: '12px'
                }}
              >
                <div style={{ fontWeight: 'bold' }}>{formatFrequency(result.frequency)}</div>
                <div style={{ color: '#999', fontSize: '11px' }}>
                  Power: {result.power?.toFixed(1) || 'N/A'} dB • 
                  SNR: {result.snr?.toFixed(1) || 'N/A'} dB
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: '16px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>Recent Scans</h4>
        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {scanHistory.length === 0 ? (
            <div style={{ padding: '12px', textAlign: 'center', color: '#999', fontSize: '12px' }}>
              No scan history
            </div>
          ) : (
            scanHistory.slice(0, 10).map((signal) => (
              <div
                key={signal.id}
                style={{
                  padding: '6px',
                  background: '#1a1a1a',
                  borderRadius: '4px',
                  marginBottom: '4px',
                  fontSize: '11px'
                }}
              >
                {formatFrequency(signal.frequency)} - {signal.category || 'unknown'} - {new Date(signal.timestamp).toLocaleString()}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default AdvancedScanner

