import React, { useState, useEffect, useRef } from 'react'

const SMeter = ({ spectrumData, tunedFrequency }) => {
  const [sValue, setSValue] = useState(0)
  const [peakValue, setPeakValue] = useState(0)
  const [power, setPower] = useState(-120)
  const peakHoldTimer = useRef(null)

  useEffect(() => {
    if (!spectrumData || !Array.isArray(spectrumData.spectrum) || spectrumData.spectrum.length === 0) return

    try {
      const spectrum = spectrumData.spectrum
      const freqs = spectrumData.frequencies

      let refPower
      if (Array.isArray(freqs) && typeof tunedFrequency === 'number') {
        // Use a ±25 kHz window around tuned frequency
        const windowHz = 25000
        const idxs = freqs
          .map((f, i) => ({ f, i }))
          .filter(x => Math.abs(x.f - tunedFrequency) <= windowHz)
          .map(x => x.i)
        const windowVals = idxs.length ? idxs.map(i => spectrum[i]) : spectrum
        // 90th percentile to be noise-robust
        const sorted = [...windowVals].sort((a, b) => a - b)
        const p90Index = Math.max(0, Math.min(sorted.length - 1, Math.floor(sorted.length * 0.9)))
        refPower = sorted[p90Index]
      } else {
        // Fallback to global max if we don't know tuned frequency
        refPower = Math.max(...spectrum)
      }

      setPower(refPower)
      const sUnits = powerToSUnits(refPower)
      setSValue(sUnits)

      // Update peak hold
      if (sUnits.total > peakValue) {
        setPeakValue(sUnits.total)

        // Clear existing timer
        if (peakHoldTimer.current) {
          clearTimeout(peakHoldTimer.current)
        }

        // Set new timer to decay peak after 2 seconds
        peakHoldTimer.current = setTimeout(() => {
          setPeakValue(0)
        }, 2000)
      }

      return () => {
        if (peakHoldTimer.current) {
          clearTimeout(peakHoldTimer.current)
        }
      }
    } catch (error) {
      console.error('Error in SMeter useEffect:', error)
    }
  }, [spectrumData, tunedFrequency])

  const powerToSUnits = (power) => {
    // S9 = -73 dBm reference level (commonly used for HF)
    // Each S-unit is 6 dB
    // For VHF/UHF, S9 is typically -93 dBm, but we'll use -73 for consistency
    const s9Level = -73

    if (power < s9Level) {
      // Below S9
      const sBelowS9 = Math.max(0, Math.min(9, 9 + Math.floor((power - s9Level) / 6)))
      return {
        s: Math.floor(sBelowS9),
        plus: 0,
        total: sBelowS9,
        overS9: false
      }
    } else {
      // Over S9
      const plusDb = power - s9Level
      return {
        s: 9,
        plus: plusDb,
        total: 9 + (plusDb / 10), // Scale for display
        overS9: true
      }
    }
  }

  const getSColor = (sTotal) => {
    if (sTotal < 3) return '#4ade80' // green
    if (sTotal < 6) return '#84cc16' // lime
    if (sTotal < 9) return '#eab308' // yellow
    if (sTotal < 12) return '#f97316' // orange
    return '#ef4444' // red
  }

  const formatSValue = (sUnits) => {
    if (sUnits.overS9) {
      return `S9+${sUnits.plus.toFixed(0)}dB`
    } else {
      return `S${Math.max(1, Math.floor(sUnits.s))}`
    }
  }

  const sPercent = Math.min(100, (sValue.total / 15) * 100) // Scale to 0-100%
  const peakPercent = Math.min(100, (peakValue / 15) * 100)

  return (
    <div className="smeter">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-bold text-gray-300">Signal Strength</h4>
        <div className="text-xs text-gray-400">
          {formatSValue(sValue)} ({power.toFixed(1)} dBm)
        </div>
      </div>

      {/* S-Meter Bar */}
      <div className="smeter-container">
        {/* Background scale */}
        <div className="smeter-scale">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(s => (
            <div key={s} className="smeter-mark" style={{ left: `${(s / 15) * 100}%` }}>
              <div className="smeter-tick"></div>
              <span className="smeter-label">{s}</span>
            </div>
          ))}
          {[10, 20, 30, 40].map(plus => (
            <div key={`plus${plus}`} className="smeter-mark" style={{ left: `${((9 + plus / 10) / 15) * 100}%` }}>
              <div className="smeter-tick"></div>
              <span className="smeter-label">+{plus}</span>
            </div>
          ))}
        </div>

        {/* Bar */}
        <div className="smeter-bar-container">
          {/* Peak hold indicator */}
          {peakValue > 0 && (
            <div 
              className="smeter-peak"
              style={{ left: `${peakPercent}%` }}
            />
          )}
          
          {/* Current level bar */}
          <div 
            className="smeter-bar"
            style={{ 
              width: `${sPercent}%`,
              backgroundColor: getSColor(sValue.total)
            }}
          />
        </div>
      </div>
    </div>
  )
}

export default SMeter

