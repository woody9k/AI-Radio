import React, { useRef, useEffect, useState } from 'react'

const SpectrumDisplay = ({ spectrumData, waterfallData, streaming, onTuneToFrequency }) => {
  const canvasRef = useRef(null)
  const waterfallRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })
  const [mousePos, setMousePos] = useState(null)
  const [dragStart, setDragStart] = useState(null)
  const [dragEnd, setDragEnd] = useState(null)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    const updateDimensions = () => {
      const container = canvasRef.current?.parentElement
      if (container) {
        setDimensions({
          width: container.clientWidth - 20,
          height: Math.max(300, container.clientHeight / 2 - 20)
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  const formatFrequency = (freq) => {
    if (!freq && freq !== 0) return 'N/A'
    
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

  const handleMouseMove = (e) => {
    if (!canvasRef.current || !spectrumData) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    setMousePos({ x, y })
    
    if (isDragging && dragStart) {
      setDragEnd({ x, y })
    }
  }

  const handleMouseDown = (e) => {
    if (!canvasRef.current) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    setDragStart({ x, y })
    setIsDragging(true)
  }

  const handleMouseUp = (e) => {
    if (!isDragging || !dragStart || !spectrumData) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    
    const width = rect.width
    const frequencies = spectrumData.frequencies
    
    if (Math.abs(x - dragStart.x) < 5) {
      // Single click - tune to frequency
      const freqIndex = Math.floor((dragStart.x / width) * frequencies.length)
      const targetFreq = frequencies[freqIndex]
      
      if (onTuneToFrequency) {
        onTuneToFrequency(targetFreq)
      }
    } else {
      // Drag - select bandwidth and tune to center
      const startIndex = Math.floor((Math.min(dragStart.x, x) / width) * frequencies.length)
      const endIndex = Math.floor((Math.max(dragStart.x, x) / width) * frequencies.length)
      
      const startFreq = frequencies[startIndex]
      const endFreq = frequencies[endIndex]
      const centerFreq = (startFreq + endFreq) / 2
      const bandwidth = Math.abs(endFreq - startFreq)
      
      if (onTuneToFrequency) {
        onTuneToFrequency(centerFreq, bandwidth)
      }
    }
    
    // Reset drag state
    setDragStart(null)
    setDragEnd(null)
    setIsDragging(false)
  }

  const handleMouseLeave = () => {
    setMousePos(null)
    if (isDragging) {
      setDragStart(null)
      setDragEnd(null)
      setIsDragging(false)
    }
  }

  const handleSignalClick = (signal) => {
    if (onTuneToFrequency) {
      onTuneToFrequency(signal.frequency, signal.bandwidth)
    }
  }

  useEffect(() => {
    if (!spectrumData || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const { width, height } = dimensions

    // Clear canvas
    ctx.fillStyle = '#0a0a0a'
    ctx.fillRect(0, 0, width, height)

    // Draw grid
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1
    
    // Horizontal grid lines
    for (let i = 0; i <= 10; i++) {
      const y = (height / 10) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()
    }

    // Vertical grid lines
    for (let i = 0; i <= 10; i++) {
      const x = (width / 10) * i
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
      ctx.stroke()
    }

    // Draw spectrum
    if (spectrumData.spectrum && spectrumData.frequencies) {
      const spectrum = spectrumData.spectrum
      const frequencies = spectrumData.frequencies
      
      // Normalize spectrum to canvas height
      const minPower = Math.min(...spectrum)
      const maxPower = Math.max(...spectrum)
      const powerRange = maxPower - minPower

      ctx.strokeStyle = '#3b82f6'
      ctx.lineWidth = 2
      ctx.beginPath()

      for (let i = 0; i < spectrum.length; i++) {
        const x = (i / (spectrum.length - 1)) * width
        const normalizedPower = (spectrum[i] - minPower) / powerRange
        const y = height - (normalizedPower * height * 0.9) - height * 0.05

        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()

      // Draw detected signals
      if (spectrumData.signals) {
        spectrumData.signals.forEach((signal, idx) => {
          const signalIndex = frequencies.findIndex(f => 
            Math.abs(f - (signal.frequency - frequencies[0])) < 1000
          )
          
          if (signalIndex !== -1) {
            const x = (signalIndex / (frequencies.length - 1)) * width
            const normalizedPower = (signal.power - minPower) / powerRange
            const y = height - (normalizedPower * height * 0.9) - height * 0.05

            // Draw signal marker
            ctx.fillStyle = signal.category && signal.category !== 'unknown' ? '#10b981' : '#ef4444'
            ctx.beginPath()
            ctx.arc(x, y, 5, 0, 2 * Math.PI)
            ctx.fill()
            
            // Draw border for clickability
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 1
            ctx.stroke()

            // Draw signal label
            ctx.fillStyle = '#ffffff'
            ctx.font = '11px Arial'
            const label = `${(signal.frequency / 1e6).toFixed(3)} MHz`
            ctx.fillText(label, x + 8, y - 8)
            
            // Show category if classified
            if (signal.category && signal.category !== 'unknown') {
              ctx.fillStyle = '#10b981'
              ctx.font = '9px Arial'
              ctx.fillText(signal.description || signal.category, x + 8, y + 4)
            }
          }
        })
      }
      
      // Draw frequency scale
      if (frequencies && frequencies.length > 0) {
        ctx.fillStyle = '#999'
        ctx.font = '12px Arial'
        const numLabels = 5
        for (let i = 0; i <= numLabels; i++) {
          const x = (i / numLabels) * width
          const freqIndex = Math.floor((i / numLabels) * frequencies.length)
          if (freqIndex < frequencies.length) {
            const freq = frequencies[freqIndex]
            const label = formatFrequency(freq)
            const labelWidth = ctx.measureText(label).width
            ctx.fillText(label, x - labelWidth / 2, height - 5)
          }
        }
      }
    }

    // Draw drag selection box
    if (isDragging && dragStart && dragEnd) {
      ctx.strokeStyle = '#3b82f6'
      ctx.fillStyle = 'rgba(59, 130, 246, 0.1)'
      ctx.lineWidth = 2
      const x = Math.min(dragStart.x, dragEnd.x)
      const w = Math.abs(dragEnd.x - dragStart.x)
      ctx.fillRect(x, 0, w, height)
      ctx.strokeRect(x, 0, w, height)
      
      // Show bandwidth label
      if (spectrumData.frequencies) {
        const frequencies = spectrumData.frequencies
        const width = dimensions.width
        const startIndex = Math.floor((Math.min(dragStart.x, dragEnd.x) / width) * frequencies.length)
        const endIndex = Math.floor((Math.max(dragStart.x, dragEnd.x) / width) * frequencies.length)
        const bandwidth = Math.abs(frequencies[endIndex] - frequencies[startIndex])
        
        ctx.fillStyle = '#3b82f6'
        ctx.font = 'bold 14px Arial'
        const bwLabel = `BW: ${formatFrequency(bandwidth)}`
        const labelWidth = ctx.measureText(bwLabel).width
        ctx.fillText(bwLabel, (dragStart.x + dragEnd.x) / 2 - labelWidth / 2, 30)
      }
    }

    // Draw mouse tooltip
    if (mousePos && !isDragging && spectrumData.frequencies && spectrumData.spectrum) {
      const frequencies = spectrumData.frequencies
      const spectrum = spectrumData.spectrum
      const freqIndex = Math.floor((mousePos.x / width) * frequencies.length)
      
      if (freqIndex >= 0 && freqIndex < frequencies.length) {
        const freq = frequencies[freqIndex]
        const power = spectrum[freqIndex]
        
        // Draw tooltip
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
        ctx.fillRect(mousePos.x + 10, mousePos.y - 40, 150, 35)
        
        ctx.fillStyle = '#ffffff'
        ctx.font = '11px Arial'
        ctx.fillText(`Freq: ${formatFrequency(freq)}`, mousePos.x + 15, mousePos.y - 25)
        ctx.fillText(`Power: ${power.toFixed(1)} dB`, mousePos.x + 15, mousePos.y - 12)
      }
    }

    // Draw labels
    ctx.fillStyle = '#ffffff'
    ctx.font = '14px Arial'
    ctx.fillText('Power (dB)', 10, 20)
    
    // Draw instructions
    ctx.fillStyle = '#666'
    ctx.font = '11px Arial'
    ctx.fillText('Click to tune | Drag to select bandwidth', 10, height - 25)

    // Draw power scale
    if (spectrumData.spectrum) {
      const minPower = Math.min(...spectrumData.spectrum)
      const maxPower = Math.max(...spectrumData.spectrum)
      
      ctx.fillStyle = '#666'
      ctx.font = '12px Arial'
      ctx.fillText(`${maxPower.toFixed(0)} dB`, 10, 35)
      ctx.fillText(`${minPower.toFixed(0)} dB`, 10, height - 40)
    }

  }, [spectrumData, dimensions, mousePos, dragStart, dragEnd, isDragging])

  useEffect(() => {
    if (!waterfallData || !waterfallRef.current) return

    const canvas = waterfallRef.current
    const ctx = canvas.getContext('2d')
    const { width, height } = dimensions

    // Clear canvas
    ctx.fillStyle = '#000000'
    ctx.fillRect(0, 0, width, height)

    // Draw waterfall data
    if (waterfallData.data) {
      const imageData = ctx.createImageData(width, height)
      const data = imageData.data

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const dataIndex = (y * width + x) * 4
          const waterfallY = Math.floor((y / height) * waterfallData.data.length)
          const waterfallX = Math.floor((x / width) * waterfallData.data[0].length)
          
          if (waterfallY < waterfallData.data.length && waterfallX < waterfallData.data[0].length) {
            const intensity = waterfallData.data[waterfallY][waterfallX] / 255
            
            // Color mapping (blue to red)
            const r = Math.floor(intensity * 255)
            const g = Math.floor(intensity * 128)
            const b = Math.floor((1 - intensity) * 255)
            
            data[dataIndex] = r     // Red
            data[dataIndex + 1] = g // Green
            data[dataIndex + 2] = b // Blue
            data[dataIndex + 3] = 255 // Alpha
          }
        }
      }

      ctx.putImageData(imageData, 0, 0)
    }

  }, [waterfallData, dimensions])

  return (
    <div className="spectrum-display">
      <div className="display-header">
        <h3>Spectrum Display</h3>
        <div className="streaming-status">
          <span className={`status ${streaming ? 'status-streaming' : 'status-disconnected'}`}>
            {streaming ? 'Streaming' : 'Stopped'}
          </span>
        </div>
      </div>

      <div className="display-content">
        {/* Spectrum Plot */}
        <div className="spectrum-plot">
          <canvas
            ref={canvasRef}
            width={dimensions.width}
            height={dimensions.height}
            style={{ border: '1px solid #333', borderRadius: '4px', cursor: 'crosshair' }}
            onMouseMove={handleMouseMove}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
          />
        </div>

        {/* Waterfall Display */}
        <div className="waterfall-display">
          <h4 className="text-sm text-gray-300 mb-2">Waterfall</h4>
          <canvas
            ref={waterfallRef}
            width={dimensions.width}
            height={Math.max(100, dimensions.height / 3)}
            style={{ border: '1px solid #333', borderRadius: '4px' }}
          />
        </div>
      </div>

      {/* Spectrum Info */}
      {spectrumData && (
        <div className="spectrum-info">
          <div className="info-grid">
            <div>
              <span className="text-gray-300">Signals Detected:</span>
              <span className="text-white ml-2">
                {spectrumData.signals ? spectrumData.signals.length : 0}
              </span>
            </div>
            <div>
              <span className="text-gray-300">Center Frequency:</span>
              <span className="text-white ml-2">
                {spectrumData.frequencies && spectrumData.frequencies.length > 0 
                  ? formatFrequency(spectrumData.frequencies[Math.floor(spectrumData.frequencies.length / 2)])
                  : 'N/A'}
              </span>
            </div>
            <div>
              <span className="text-gray-300">Span:</span>
              <span className="text-white ml-2">
                {spectrumData.frequencies && spectrumData.frequencies.length > 1
                  ? formatFrequency(spectrumData.frequencies[spectrumData.frequencies.length - 1] - spectrumData.frequencies[0])
                  : 'N/A'}
              </span>
            </div>
            <div>
              <span className="text-gray-300">Last Update:</span>
              <span className="text-white ml-2">
                {new Date(spectrumData.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SpectrumDisplay
