import React, { useRef, useEffect, useState } from 'react'

const SpectrumDisplay = ({ spectrumData, waterfallData, streaming }) => {
  const canvasRef = useRef(null)
  const waterfallRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })

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
        const y = height - (normalizedPower * height)

        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()

      // Draw detected signals
      if (spectrumData.signals) {
        spectrumData.signals.forEach(signal => {
          const signalIndex = frequencies.findIndex(f => 
            Math.abs(f - (signal.frequency - spectrumData.frequencies[0])) < 1000
          )
          
          if (signalIndex !== -1) {
            const x = (signalIndex / (frequencies.length - 1)) * width
            const normalizedPower = (signal.power - minPower) / powerRange
            const y = height - (normalizedPower * height)

            // Draw signal marker
            ctx.fillStyle = '#ef4444'
            ctx.beginPath()
            ctx.arc(x, y, 4, 0, 2 * Math.PI)
            ctx.fill()

            // Draw signal label
            ctx.fillStyle = '#ffffff'
            ctx.font = '12px Arial'
            ctx.fillText(
              `${(signal.frequency / 1e6).toFixed(3)} MHz`,
              x + 8,
              y - 8
            )
          }
        })
      }
    }

    // Draw labels
    ctx.fillStyle = '#ffffff'
    ctx.font = '14px Arial'
    ctx.fillText('Power (dB)', 10, 20)
    ctx.fillText('Frequency', width - 100, height - 10)

    // Draw power scale
    if (spectrumData.spectrum) {
      const minPower = Math.min(...spectrumData.spectrum)
      const maxPower = Math.max(...spectrumData.spectrum)
      
      ctx.fillStyle = '#666'
      ctx.font = '12px Arial'
      ctx.fillText(`${maxPower.toFixed(0)} dB`, 10, 30)
      ctx.fillText(`${minPower.toFixed(0)} dB`, 10, height - 10)
    }

  }, [spectrumData, dimensions])

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
            style={{ border: '1px solid #333', borderRadius: '4px' }}
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


