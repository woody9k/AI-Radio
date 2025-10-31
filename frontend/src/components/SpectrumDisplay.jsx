import React, { useRef, useEffect, useState, useMemo } from 'react'

const SpectrumDisplay = ({ spectrumData, waterfallData, streaming, onTuneToFrequency, currentFrequency, currentBandwidth, onListenToSignal, onBookmarkSignal }) => {
  const canvasRef = useRef(null)
  const waterfallRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })
  const [inputFrequency, setInputFrequency] = useState(currentFrequency || 100000000)
  const [mousePos, setMousePos] = useState(null)
  const [dragStart, setDragStart] = useState(null)
  const [dragEnd, setDragEnd] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [viewRange, setViewRange] = useState({ start: 0, end: 1 }) // fraction [0..1]
  const [panning, setPanning] = useState(false)
  // Zoom and dBFS range controls
  const [zoomLevel, setZoomLevel] = useState(0) // 0..1 (0 = full span)
  const [dbfsBottom, setDbfsBottom] = useState(-120) // bottom when autoscale disabled
  // Spectrum scaling/smoothing
  const [autoScale, setAutoScale] = useState(true)
  const [userMinDb, setUserMinDb] = useState(-120)
  const [userMaxDb, setUserMaxDb] = useState(0)
  const [smoothEnabled, setSmoothEnabled] = useState(false)
  const [smoothAlpha, setSmoothAlpha] = useState(0.5)
  const [avgEnabled, setAvgEnabled] = useState(false)
  const [peakEnabled, setPeakEnabled] = useState(false)
  const avgBufferRef = useRef(null)
  const peakBufferRef = useRef(null)
  const prevSliceRef = useRef(null)
  const lastRetuneRef = useRef(0)
  // Waterfall polish
  const [waterfallPaused, setWaterfallPaused] = useState(false)
  const [waterfallColormap, setWaterfallColormap] = useState('viridis')
  const [waterfallBrightness, setWaterfallBrightness] = useState(1.0)
  const [waterfallContrast, setWaterfallContrast] = useState(1.0)
  const [waterfallRate, setWaterfallRate] = useState(1) // draw every Nth frame
  const [waterfallAutoGain, setWaterfallAutoGain] = useState(false)
  const waterfallFrameRef = useRef(0)
  const [zoomData, setZoomData] = useState(null) // high-res spectrum slice

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
    if (currentFrequency) {
      setInputFrequency(currentFrequency)
    }
  }, [currentFrequency])

  const clampFrequency = (value) => {
    // Clamp to a broad RF range, not the current FFT span
    const MIN_RF = 0
    const MAX_RF = 6e9 // 6 GHz upper guard; adjust if device caps are known
    const v = Math.round(value || 0)
    return Math.max(MIN_RF, Math.min(MAX_RF, v))
  }

  const handleFrequencyStepAtPower = (power) => {
    const step = Math.pow(10, power)
    const next = clampFrequency((inputFrequency || 0) + step)
    setInputFrequency(next)
    if (onTuneToFrequency) onTuneToFrequency(next)
  }

  const handleFrequencyDownAtPower = (power) => {
    const step = Math.pow(10, power)
    const next = clampFrequency((inputFrequency || 0) - step)
    setInputFrequency(next)
    if (onTuneToFrequency) onTuneToFrequency(next)
  }

  const freqDigits = useMemo(() => {
    const f = Math.max(0, Math.round(inputFrequency || 0))
    const pad = (n, w) => n.toString().padStart(w, '0')
    const ghz = Math.floor(f / 1e9)
    const mhz = Math.floor((f % 1e9) / 1e6)
    const khz = Math.floor((f % 1e6) / 1e3)
    const hz = Math.floor(f % 1e3)
    return { ghz, mhz: pad(mhz, 3), khz: pad(khz, 3), hz: pad(hz, 3) }
  }, [inputFrequency])

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

  // Fetch high-res zoom data when span < threshold
  useEffect(() => {
    if (!spectrumData || !Array.isArray(spectrumData.absolute_frequencies || spectrumData.frequencies)) { setZoomData(null); return }
    const freqs = spectrumData.absolute_frequencies || spectrumData.frequencies
    if (!freqs.length) { setZoomData(null); return }
    const startIdx = Math.floor(viewRange.start * (freqs.length - 1))
    const endIdx = Math.floor(viewRange.end * (freqs.length - 1))
    const spanHz = Math.abs(freqs[endIdx] - freqs[startIdx])
    const centerHz = (freqs[startIdx] + freqs[endIdx]) / 2
    const threshold = 100000 // 100 kHz
    if (spanHz < threshold) {
      const controller = new AbortController()
      const url = `/api/spectrum/zoom?center=${Math.round(centerHz)}&span=${Math.max(5000, Math.round(spanHz))}&fft=8192`
      fetch(url, { signal: controller.signal })
        .then(r => r.json())
        .then(d => { if (d && d.success) setZoomData(d); else setZoomData(null) })
        .catch(() => {})
      return () => controller.abort()
    } else {
      setZoomData(null)
    }
  }, [spectrumData, viewRange])

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
    
    // Passband edge drag detection
    if ((spectrumData.absolute_frequencies || spectrumData.frequencies) && typeof currentFrequency === 'number' && typeof currentBandwidth === 'number' && currentBandwidth > 0) {
      const freqs = (zoomData?.absolute_frequencies || spectrumData.absolute_frequencies || spectrumData.frequencies)
      const startIdx = Math.floor(viewRange.start * (freqs.length - 1))
      const endIdx = Math.floor(viewRange.end * (freqs.length - 1))
      const length = Math.max(2, endIdx - startIdx + 1)
      const leftTarget = currentFrequency - currentBandwidth / 2
      const rightTarget = currentFrequency + currentBandwidth / 2
      let li = startIdx
      for (let i = startIdx + 1; i <= endIdx; i++) { if (freqs[i] >= leftTarget) { li = i; break } }
      let ri = endIdx
      for (let i = li; i <= endIdx; i++) { if (freqs[i] >= rightTarget) { ri = i; break } }
      const lx = ((li - startIdx) / (length - 1)) * rect.width
      const rx = ((ri - startIdx) / (length - 1)) * rect.width
      const hit = 6
      if (Math.abs(x - lx) <= hit || Math.abs(x - rx) <= hit) {
        // Start dragging the nearest edge
        const draggingLeft = Math.abs(x - lx) <= Math.abs(x - rx)
        setPanning(false)
        setDragStart({ x, y, passbandDrag: draggingLeft ? 'left' : 'right' })
        setIsDragging(true)
        return
      }
    }

    // Detect double-click to center on cursor
    if (e.detail === 2 && spectrumData && (spectrumData.absolute_frequencies || spectrumData.frequencies)) {
      const freqs = spectrumData.absolute_frequencies || spectrumData.frequencies
      const startIdx = Math.floor(viewRange.start * (freqs.length - 1))
      const endIdx = Math.floor(viewRange.end * (freqs.length - 1))
      const rel = Math.min(1, Math.max(0, x / rect.width))
      const idx = startIdx + Math.floor(rel * Math.max(1, endIdx - startIdx))
      const target = freqs[Math.max(startIdx, Math.min(endIdx, idx))]
      if (onTuneToFrequency && typeof target === 'number') {
        onTuneToFrequency(target)
      }
      return
    }

    if (e.button === 2 || e.shiftKey) {
      setPanning(true)
      setDragStart({ x, y })
    } else {
      setDragStart({ x, y })
      setIsDragging(true)
    }
  }

  const handleMouseUp = (e) => {
    if (panning) {
      setPanning(false)
      setDragStart(null)
      setDragEnd(null)
      return
    }
    if (!isDragging || !dragStart || !spectrumData) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    
    const width = rect.width
    const frequencies = spectrumData.frequencies
    const spectrum = spectrumData.spectrum || []
    const startIdx = Math.floor(viewRange.start * (frequencies.length - 1))
    const endIdx = Math.floor(viewRange.end * (frequencies.length - 1))
    const length = Math.max(2, endIdx - startIdx + 1)
    
    // If dragging passband edge, compute new bandwidth and apply
    if (dragStart && dragStart.passbandDrag && (spectrumData.absolute_frequencies || spectrumData.frequencies)) {
      const freqs = spectrumData.absolute_frequencies || spectrumData.frequencies
      const rel = Math.min(1, Math.max(0, x / width))
      const idx = startIdx + Math.floor(rel * Math.max(1, endIdx - startIdx))
      const edgeFreq = freqs[Math.min(endIdx, Math.max(startIdx, idx))]
      const otherEdge = dragStart.passbandDrag === 'left' ? (currentFrequency + (currentBandwidth || 0) / 2) : (currentFrequency - (currentBandwidth || 0) / 2)
      const newBw = Math.abs(edgeFreq - otherEdge)
      const newCenter = (edgeFreq + otherEdge) / 2
      if (onTuneToFrequency && newBw > 0) onTuneToFrequency(newCenter, newBw)
      setDragStart(null)
      setDragEnd(null)
      setIsDragging(false)
      return
    }

    if (Math.abs(x - dragStart.x) < 5) {
      // Single click
      // If clicked near a signal marker, act on marker
      const visMinF = frequencies[startIdx]
      const visMaxF = frequencies[endIdx]
      let closest = null
      let minDist = Infinity
      const minPower = Math.min(...spectrum.slice(startIdx, endIdx + 1))
      const maxPower = Math.max(...spectrum.slice(startIdx, endIdx + 1))
      const powerRange = (maxPower - minPower) || 1
      if (spectrumData.signals) {
        spectrumData.signals.forEach((sig) => {
          if (sig.frequency < visMinF || sig.frequency > visMaxF) return
          let si = startIdx
          for (let i = startIdx + 1; i <= endIdx; i++) { if (frequencies[i] >= sig.frequency) { si = i; break } }
          const px = ((si - startIdx) / (length - 1)) * width
          const normP = ((sig.power ?? minPower) - minPower) / powerRange
          const py = rect.height - (normP * rect.height * 0.9) - rect.height * 0.05
          const dx = dragStart.x - px
          const dy = dragStart.y - py
          const d2 = dx*dx + dy*dy
          if (d2 < minDist) { minDist = d2; closest = sig }
        })
      }
      const hitRadius2 = 10 * 10
      if (closest && minDist <= hitRadius2) {
        // Shift-click to bookmark; Alt or Ctrl to listen; default to tune
        if (e.shiftKey && onBookmarkSignal) onBookmarkSignal(closest)
        else if ((e.altKey || e.ctrlKey) && onListenToSignal) onListenToSignal(closest)
        else if (onTuneToFrequency) onTuneToFrequency(closest.frequency, closest.bandwidth)
      } else {
        const rel = dragStart.x / width
        const idx = startIdx + Math.floor(rel * Math.max(1, endIdx - startIdx))
        const freqIndex = Math.min(frequencies.length - 1, Math.max(0, idx))
        let targetFreq = frequencies[freqIndex]
        // Snap-to-step (1 kHz grid for now)
        const step = 1000
        targetFreq = Math.round(targetFreq / step) * step
        if (onTuneToFrequency) onTuneToFrequency(targetFreq)
      }
    } else {
      // Drag - select bandwidth and tune to center
      const sx = Math.min(dragStart.x, x)
      const ex = Math.max(dragStart.x, x)
      const startIndex = startIdx + Math.floor((sx / width) * Math.max(1, endIdx - startIdx))
      const endIndex = startIdx + Math.floor((ex / width) * Math.max(1, endIdx - startIdx))
      
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
    if (panning) {
      setPanning(false)
      setDragStart(null)
      setDragEnd(null)
    }
  }

  // click handling occurs via mouse events above

  // Prevent context menu on right-drag pan
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const handler = (e) => e.preventDefault()
    canvas.addEventListener('contextmenu', handler)
    return () => canvas.removeEventListener('contextmenu', handler)
  }, [])

  // Wheel zoom around cursor
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const onWheel = (e) => {
      if (!spectrumData || !(spectrumData.absolute_frequencies || spectrumData.frequencies)) return
      e.preventDefault()
      const rect = canvas.getBoundingClientRect()
      const cursor = (e.clientX - rect.left) / rect.width
      const range = viewRange.end - viewRange.start
      if (e.altKey) {
        // Alt + wheel: fine pan left/right
        const panFrac = (e.deltaY > 0 ? 1 : -1) * 0.02 * Math.max(0.001, range)
        let start = Math.max(0, Math.min(1 - range, viewRange.start + panFrac))
        let end = start + range
        setViewRange({ start, end })
        return
      }
      // Zoom
      const zoomBase = e.ctrlKey ? 0.85 : (e.shiftKey ? 0.8 : 0.9)
      const expand = e.deltaY < 0 ? zoomBase : 1 / zoomBase
      const newRange = Math.min(1, Math.max(0.001, range * expand))
      const center = viewRange.start + range * cursor
      let start = center - newRange * cursor
      let end = start + newRange
      if (start < 0) { end -= start; start = 0 }
      if (end > 1) { const over = end - 1; start -= over; end = 1; if (start < 0) start = 0 }
      setViewRange({ start, end })
    }
    canvas.addEventListener('wheel', onWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', onWheel)
  }, [viewRange, spectrumData])

  // Map zoomLevel -> viewRange width, keeping center stable
  useEffect(() => {
    const minFrac = 0.001
    const z = Math.max(0, Math.min(1, zoomLevel))
    const frac = minFrac * Math.pow(1 / minFrac, 1 - z)
    const current = viewRange.end - viewRange.start
    if (Math.abs(current - frac) < 1e-6) return
    const center = viewRange.start + current / 2
    let start = center - frac / 2
    let end = center + frac / 2
    if (start < 0) { end -= start; start = 0 }
    if (end > 1) { const over = end - 1; start -= over; end = 1; if (start < 0) start = 0 }
    setViewRange({ start, end })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoomLevel])

  // Map viewRange width -> zoomLevel, so wheel/pan keeps slider in sync
  useEffect(() => {
    const minFrac = 0.001
    const frac = Math.min(1, Math.max(minFrac, viewRange.end - viewRange.start))
    const z = 1 - Math.log(frac / minFrac) / Math.log(1 / minFrac)
    const clamped = Math.max(0, Math.min(1, z))
    if (Math.abs(clamped - zoomLevel) > 0.002) setZoomLevel(clamped)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewRange])

  // Right/Shift drag pan
  useEffect(() => {
    if (!panning || !dragStart || !canvasRef.current) return
    const onMove = (e) => {
      const rect = canvasRef.current.getBoundingClientRect()
      const dx = (e.clientX - rect.left - dragStart.x) / rect.width
      const range = viewRange.end - viewRange.start
      let start = viewRange.start - dx
      let end = start + range
      if (start < 0) { end -= start; start = 0 }
      if (end > 1) { const over = end - 1; start -= over; end = 1; if (start < 0) start = 0 }
      setViewRange({ start, end })
      setDragEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top })

      // Edge retune: if near edges, retune to center of current view
      const now = Date.now()
      const shouldRetune = (start < 0.03 || end > 0.97) && (now - lastRetuneRef.current > 700)
      if (shouldRetune && spectrumData && spectrumData.frequencies && onTuneToFrequency) {
        const freqs = spectrumData.frequencies
        const startIdx = Math.floor(Math.max(0, Math.min(1, start)) * (freqs.length - 1))
        const endIdx = Math.floor(Math.max(0, Math.min(1, end)) * (freqs.length - 1))
        const centerIdx = Math.floor((startIdx + endIdx) / 2)
        const target = freqs[Math.max(0, Math.min(freqs.length - 1, centerIdx))]
        lastRetuneRef.current = now
        onTuneToFrequency(target)
        // Recenter view around 0.5 to keep span after retune
        const newStart = Math.max(0, 0.5 - range / 2)
        const newEnd = Math.min(1, 0.5 + range / 2)
        setViewRange({ start: newStart, end: newEnd })
      }
    }
    const onUp = () => { setPanning(false); setDragStart(null); setDragEnd(null) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp, { once: true })
    return () => { window.removeEventListener('mousemove', onMove) }
  }, [panning, dragStart, viewRange])

  const spectrumRafRef = useRef(0)
  const fpsRef = useRef({ last: (typeof performance !== 'undefined' ? performance.now() : Date.now()), frames: 0, fps: 0 })
  useEffect(() => {
    if (!spectrumData || !canvasRef.current) return

    const draw = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const { width, height } = dimensions

    // Theme colors from CSS variables
    const styles = getComputedStyle(document.documentElement)
    const colorGrid = styles.getPropertyValue('--grid') || '#333'
    const colorSpectrum = styles.getPropertyValue('--spectrum') || '#9ca3af'
    const colorSignal = styles.getPropertyValue('--signal') || '#3b82f6'
    const colorSignalUnknown = styles.getPropertyValue('--signal-unknown') || '#ef4444'
    const colorText = styles.getPropertyValue('--text') || '#ffffff'
    const colorMuted = styles.getPropertyValue('--muted') || '#999'
    const colorTooltip = styles.getPropertyValue('--tooltip-bg') || 'rgba(0,0,0,0.8)'
    const colorAccent = styles.getPropertyValue('--accent') || '#f59e0b'

    // Clear canvas
    ctx.fillStyle = '#0a0a0a'
    ctx.fillRect(0, 0, width, height)

    // Draw grid
    ctx.strokeStyle = colorGrid.trim()
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

    // Determine data source (use zoomData if available)
    const useData = zoomData && Array.isArray(zoomData.spectrum) && Array.isArray(zoomData.absolute_frequencies) ? zoomData : spectrumData
    // Draw spectrum (slice by viewRange)
    if (useData.spectrum && (useData.absolute_frequencies || useData.frequencies)) {
      const spectrum = useData.spectrum
      const frequencies = useData.absolute_frequencies || useData.frequencies
      const startIdx = Math.floor(viewRange.start * (spectrum.length - 1))
      const endIdx = Math.floor(viewRange.end * (spectrum.length - 1))
      const length = Math.max(2, endIdx - startIdx + 1)
      
      // Normalize spectrum to canvas height
      let slice = spectrum.slice(startIdx, endIdx + 1)
      if (smoothEnabled) {
        const prev = prevSliceRef.current
        if (prev && prev.length === slice.length) {
          slice = slice.map((v, i) => smoothAlpha * v + (1 - smoothAlpha) * prev[i])
        }
        prevSliceRef.current = slice
      } else {
        prevSliceRef.current = slice
      }
      const autoMin = Math.min(...slice)
      const autoMax = Math.max(...slice)
      // When autoscale disabled via Range slider, fix top at -30 dBFS and bottom at dbfsBottom
      const minPower = autoScale ? autoMin : dbfsBottom
      const maxPower = autoScale ? autoMax : -30
      const powerRange = (maxPower - minPower) || 1

      ctx.strokeStyle = colorSpectrum.trim()
      ctx.lineWidth = 2
      ctx.beginPath()

      for (let i = 0; i < length; i++) {
        const x = (i / (length - 1)) * width
        const normalizedPower = (slice[i] - minPower) / powerRange
        const y = height - (normalizedPower * height * 0.9) - height * 0.05

        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()

      // Average trace
      if (avgEnabled) {
        const prev = avgBufferRef.current
        const alpha = 0.2
        const next = prev && prev.length === slice.length ? slice.map((v, i) => alpha * v + (1 - alpha) * prev[i]) : slice.slice()
        avgBufferRef.current = next
        ctx.strokeStyle = '#22c55e'
        ctx.lineWidth = 1
        ctx.beginPath()
        for (let i = 0; i < length; i++) {
          const x = (i / (length - 1)) * width
          const normalizedPower = (next[i] - minPower) / powerRange
          const y = height - (normalizedPower * height * 0.9) - height * 0.05
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
      }

      // Peak hold trace
      if (peakEnabled) {
        const prev = peakBufferRef.current
        const next = prev && prev.length === slice.length ? slice.map((v, i) => Math.max(v, prev[i])) : slice.slice()
        peakBufferRef.current = next
        ctx.strokeStyle = '#f59e0b'
        ctx.lineWidth = 1
        ctx.beginPath()
        for (let i = 0; i < length; i++) {
          const x = (i / (length - 1)) * width
          const normalizedPower = (next[i] - minPower) / powerRange
          const y = height - (normalizedPower * height * 0.9) - height * 0.05
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
      }

      // Tuned frequency marker (vertical line) and passband overlay
      if (typeof currentFrequency === 'number') {
        // Find nearest index for the tuned frequency
        const minF = frequencies[startIdx]
        const maxF = frequencies[endIdx]
        if (currentFrequency >= minF && currentFrequency <= maxF) {
          // Compute x position by nearest index
          let idx = startIdx
          for (let i = startIdx + 1; i <= endIdx; i++) { if (frequencies[i] >= currentFrequency) { idx = i; break } }
          const x = ((idx - startIdx) / (length - 1)) * width
          // Vertical line
          ctx.strokeStyle = colorAccent.trim()
          ctx.setLineDash([4, 4])
          ctx.lineWidth = 2
          ctx.beginPath()
          ctx.moveTo(x, 0)
          ctx.lineTo(x, height)
          ctx.stroke()
          ctx.setLineDash([])

          // Label
          ctx.fillStyle = colorAccent.trim()
          ctx.font = '12px Arial'
          const label = `Tune: ${formatFrequency(currentFrequency)}`
          const labelWidth = ctx.measureText(label).width
          ctx.fillText(label, Math.min(Math.max(4, x - labelWidth / 2), width - labelWidth - 4), 18)

          // Passband overlay: use currentBandwidth to draw filled rectangle and draggable edges
          if (typeof currentBandwidth === 'number' && currentBandwidth > 0) {
            const half = currentBandwidth / 2
            const leftTarget = currentFrequency - half
            const rightTarget = currentFrequency + half
            // Find nearest indices for left/right within overall frequencies
            let li = startIdx
            for (let i = startIdx + 1; i <= endIdx; i++) { if (frequencies[i] >= leftTarget) { li = i; break } }
            let ri = endIdx
            for (let i = li; i <= endIdx; i++) { if (frequencies[i] >= rightTarget) { ri = i; break } }
            const lx = ((li - startIdx) / (length - 1)) * width
            const rx = ((ri - startIdx) / (length - 1)) * width

            // Draw left/right lines (edges)
            ctx.strokeStyle = colorAccent.trim()
            ctx.lineWidth = 2
            ctx.beginPath(); ctx.moveTo(lx, 0); ctx.lineTo(lx, height); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(rx, 0); ctx.lineTo(rx, height); ctx.stroke()

            // Fill between edges
            ctx.fillStyle = 'rgba(59, 130, 246, 0.08)'
            ctx.fillRect(Math.min(lx, rx), 0, Math.abs(rx - lx), height)
          }
        }
      }

      // Draw detected signals
      if (spectrumData.signals) {
        const visMinF = frequencies[startIdx]
        const visMaxF = frequencies[endIdx]
        spectrumData.signals.forEach((signal) => {
          if (signal.frequency < visMinF || signal.frequency > visMaxF) return
          let signalIndex = startIdx
          for (let i = startIdx + 1; i <= endIdx; i++) { if (frequencies[i] >= signal.frequency) { signalIndex = i; break } }
          if (signalIndex !== -1) {
            const x = ((signalIndex - startIdx) / (length - 1)) * width
            const normalizedPower = ((signal.power ?? minPower) - minPower) / powerRange
            const y = height - (normalizedPower * height * 0.9) - height * 0.05

            // Draw signal marker
            ctx.fillStyle = (signal.category && signal.category !== 'unknown') ? colorSignal.trim() : colorSignalUnknown.trim()
            ctx.beginPath()
            ctx.arc(x, y, 5, 0, 2 * Math.PI)
            ctx.fill()
            
            // Draw border for clickability
            ctx.strokeStyle = colorText.trim()
            ctx.lineWidth = 1
            ctx.stroke()

            // Draw signal label
            ctx.fillStyle = colorText.trim()
            ctx.font = '11px Arial'
            const label = `${(signal.frequency / 1e6).toFixed(3)} MHz`
            ctx.fillText(label, x + 8, y - 8)
            
            // Show category if classified
            if (signal.category && signal.category !== 'unknown') {
              ctx.fillStyle = colorSignal.trim()
              ctx.font = '9px Arial'
              ctx.fillText(signal.description || signal.category, x + 8, y + 4)
            }
          }
        })
      }
      
      // Draw frequency scale reflecting current zoom slice
      if (frequencies && frequencies.length > 0) {
        ctx.fillStyle = colorMuted.trim()
        ctx.font = '12px Arial'
        const numLabels = 5
        const total = Math.max(1, endIdx - startIdx)
        for (let i = 0; i <= numLabels; i++) {
          const x = (i / numLabels) * width
          const idx = startIdx + Math.floor((i / numLabels) * total)
          if (idx >= startIdx && idx <= endIdx) {
            const freq = frequencies[idx]
            const label = formatFrequency(freq)
            const labelWidth = ctx.measureText(label).width
            ctx.fillText(label, x - labelWidth / 2, height - 5)
          }
        }
      }

      // Draw left vertical axis ticks from -30 dBFS (top) to dbfsBottom (bottom)
      ctx.fillStyle = colorMuted.trim()
      ctx.font = '12px Arial'
      const ticks = 8
      for (let i = 0; i < ticks; i++) {
        const tDb = maxPower - (i * (maxPower - minPower) / (ticks - 1))
        const y = height - (((tDb - minPower) / (maxPower - minPower)) * height * 0.9) - height * 0.05
        ctx.strokeStyle = colorGrid.trim()
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
        const lbl = `${tDb.toFixed(0)} dBFS`
        ctx.fillStyle = colorMuted.trim()
        ctx.fillText(lbl, 10, Math.min(height - 5, Math.max(15, y - 2)))
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
      
      // Show bandwidth label with respect to current zoom slice
      if (useData.absolute_frequencies || useData.frequencies) {
        const frequencies = useData.absolute_frequencies || useData.frequencies
        const width = dimensions.width
        const visStartIdx = Math.floor(viewRange.start * (frequencies.length - 1))
        const visEndIdx = Math.floor(viewRange.end * (frequencies.length - 1))
        const visLen = Math.max(1, visEndIdx - visStartIdx)
        const sxRel = Math.min(1, Math.max(0, Math.min(dragStart.x, dragEnd.x) / width))
        const exRel = Math.min(1, Math.max(0, Math.max(dragStart.x, dragEnd.x) / width))
        const startIndex = visStartIdx + Math.floor(sxRel * visLen)
        const endIndex = visStartIdx + Math.floor(exRel * visLen)
        const safeStart = Math.min(visEndIdx, Math.max(visStartIdx, startIndex))
        const safeEnd = Math.min(visEndIdx, Math.max(visStartIdx, endIndex))
        const bandwidth = Math.abs(frequencies[safeEnd] - frequencies[safeStart])
        
        ctx.fillStyle = '#3b82f6'
        ctx.font = 'bold 14px Arial'
        const bwLabel = `BW: ${formatFrequency(bandwidth)}`
        const labelWidth = ctx.measureText(bwLabel).width
        ctx.fillText(bwLabel, (dragStart.x + dragEnd.x) / 2 - labelWidth / 2, 30)
      }
    }

    // Draw mouse tooltip (respect current zoom slice)
    if (mousePos && !isDragging && (spectrumData.absolute_frequencies || spectrumData.frequencies) && spectrumData.spectrum) {
      const frequencies = spectrumData.absolute_frequencies || spectrumData.frequencies
      const spectrum = spectrumData.spectrum
      const visStartIdx = Math.floor(viewRange.start * (frequencies.length - 1))
      const visEndIdx = Math.floor(viewRange.end * (frequencies.length - 1))
      const visLen = Math.max(1, visEndIdx - visStartIdx)
      const rel = Math.min(1, Math.max(0, mousePos.x / width))
      const freqIndex = visStartIdx + Math.floor(rel * visLen)
      
      if (freqIndex >= visStartIdx && freqIndex <= visEndIdx) {
        const freq = frequencies[freqIndex]
        const power = spectrum[freqIndex]
        
        // Draw tooltip
        ctx.fillStyle = colorTooltip.trim()
        ctx.fillRect(mousePos.x + 10, mousePos.y - 40, 150, 35)
        
        ctx.fillStyle = colorText.trim()
        ctx.font = '11px Arial'
        ctx.fillText(`Freq: ${formatFrequency(freq)}`, mousePos.x + 15, mousePos.y - 25)
        ctx.fillText(`Power: ${power.toFixed(1)} dB`, mousePos.x + 15, mousePos.y - 12)
      }
    }

    // Draw labels
    ctx.fillStyle = colorText.trim()
    ctx.font = '14px Arial'
    ctx.fillText('Power (dBFS)', 10, 20)
    
    // Draw instructions
    ctx.fillStyle = colorMuted.trim()
    ctx.font = '11px Arial'
    ctx.fillText('Click to tune | Drag to select bandwidth', 10, height - 25)

    // Debug overlay (SR, FFT, Hz/bin, FPS)
    try {
      const sr = spectrumData.sample_rate
      const res = spectrumData.resolution_hz
      const hzPerBin = typeof res === 'number' ? res : (spectrumData.frequencies && spectrumData.frequencies.length > 1 ? Math.abs(spectrumData.frequencies[1] - spectrumData.frequencies[0]) : 0)
      const fftSize = spectrumData.spectrum ? spectrumData.spectrum.length : 0
      const fps = fpsRef.current.fps
      const text = `SR: ${sr ? (sr/1e6).toFixed(3)+' MS/s' : 'n/a'} | FFT: ${fftSize} | Res: ${hzPerBin ? (hzPerBin>=1e3?(hzPerBin/1e3).toFixed(1)+' kHz': hzPerBin.toFixed(0)+' Hz') : 'n/a'} | FPS: ${fps}`
      const pad = 6
      const boxW = 320
      const boxH = 22
      ctx.fillStyle = 'rgba(0,0,0,0.5)'
      ctx.fillRect(width - boxW - pad, pad, boxW, boxH)
      ctx.fillStyle = '#ddd'
      ctx.font = '12px Arial'
      ctx.fillText(text, width - boxW - pad + 8, pad + 16)
    } catch (_) {}

    }

    cancelAnimationFrame(spectrumRafRef.current)
    spectrumRafRef.current = requestAnimationFrame(() => {
      const now = (typeof performance !== 'undefined' ? performance.now() : Date.now())
      fpsRef.current.frames += 1
      if (now - fpsRef.current.last >= 500) {
        fpsRef.current.fps = Math.round((fpsRef.current.frames * 1000) / (now - fpsRef.current.last))
        fpsRef.current.last = now
        fpsRef.current.frames = 0
      }
      draw()
    })
    return () => cancelAnimationFrame(spectrumRafRef.current)
  }, [spectrumData, dimensions, mousePos, dragStart, dragEnd, isDragging, viewRange, autoScale, userMinDb, userMaxDb, smoothEnabled, smoothAlpha])

  useEffect(() => {
    if (!waterfallData || !waterfallRef.current) return
    if (waterfallPaused) return

    const canvas = waterfallRef.current
    const ctx = canvas.getContext('2d')
    const { width, height } = dimensions

    // Clear canvas
    ctx.fillStyle = '#000000'
    ctx.fillRect(0, 0, width, height)

    // Draw waterfall data with rate limit and optional auto-gain
    if (waterfallData.data) {
      waterfallFrameRef.current = (waterfallFrameRef.current + 1) % Math.max(1, waterfallRate)
      if (waterfallFrameRef.current !== 0) return
      const imageData = ctx.createImageData(width, height)
      const data = imageData.data

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const dataIndex = (y * width + x) * 4
          const waterfallY = Math.floor((y / height) * waterfallData.data.length)
          const waterfallX = Math.floor((x / width) * waterfallData.data[0].length)
          
          if (waterfallY < waterfallData.data.length && waterfallX < waterfallData.data[0].length) {
            let intensity = waterfallData.data[waterfallY][waterfallX] / 255
            // Apply contrast/brightness
            if (waterfallAutoGain) {
              // Simple auto-gain: normalize around mid with slight stretch
              intensity = Math.min(1, Math.max(0, (intensity - 0.4) * 1.4))
            }
            intensity = Math.min(1, Math.max(0, ((intensity - 0.5) * waterfallContrast + 0.5) * waterfallBrightness))
            let r=0,g=0,b=0
            if (waterfallColormap === 'grayscale') {
              const v = Math.floor(intensity * 255)
              r = v; g = v; b = v
            } else if (waterfallColormap === 'fire') {
              r = Math.floor(255 * Math.min(1, intensity * 1.5))
              g = Math.floor(255 * Math.min(1, Math.max(0, (intensity - 0.3) * 1.2)))
              b = Math.floor(255 * Math.max(0, intensity - 0.6))
            } else {
              const t = intensity
              r = Math.floor(255 * Math.min(1, Math.max(0, -0.5 + 4.0*t - 4.0*t*t)))
              g = Math.floor(255 * Math.min(1, Math.max(0, 1.5 - 4.0*Math.abs(t-0.5))))
              b = Math.floor(255 * Math.min(1, Math.max(0, 1.0 - 4.0*(t-0.75)*(t-0.75))))
            }
            
            data[dataIndex] = r     // Red
            data[dataIndex + 1] = g // Green
            data[dataIndex + 2] = b // Blue
            data[dataIndex + 3] = 255 // Alpha
          }
        }
      }

      ctx.putImageData(imageData, 0, 0)
    }

  }, [waterfallData, dimensions, waterfallPaused, waterfallColormap, waterfallBrightness, waterfallContrast])

  return (
    <div className="spectrum-display">
      <div className="display-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Spectrum Display</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div className="digit-strip" style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <DigitGroup label="GHz" value={freqDigits.ghz} powers={[9]} onUp={handleFrequencyStepAtPower} onDown={handleFrequencyDownAtPower} />
              <span style={{ opacity: 0.6 }}>.</span>
              <DigitGroup label="MHz" value={freqDigits.mhz} powers={[8,7,6]} onUp={handleFrequencyStepAtPower} onDown={handleFrequencyDownAtPower} />
              <span style={{ opacity: 0.6 }}>.</span>
              <DigitGroup label="kHz" value={freqDigits.khz} powers={[5,4,3]} onUp={handleFrequencyStepAtPower} onDown={handleFrequencyDownAtPower} />
              <span style={{ opacity: 0.6 }}>.</span>
              <DigitGroup label="Hz" value={freqDigits.hz} powers={[2,1,0]} onUp={handleFrequencyStepAtPower} onDown={handleFrequencyDownAtPower} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label className="text-sm text-gray-300" htmlFor="header-frequency" style={{ whiteSpace: 'nowrap' }}>Frequency</label>
              <input
                id="header-frequency"
                type="number"
                value={Math.round(inputFrequency || 0)}
                onChange={(e)=>setInputFrequency(parseFloat(e.target.value)||0)}
                onKeyDown={(e)=>{ if (e.key === 'Enter' && onTuneToFrequency) { onTuneToFrequency(inputFrequency) } }}
                onBlur={()=>{ if (onTuneToFrequency) { onTuneToFrequency(inputFrequency) } }}
                className="input"
                style={{ width: 180, padding: '4px 6px', fontSize: '12px' }}
                step="1000"
              />
            </div>
          </div>
          <div className="streaming-status">
            <span className={`status ${streaming ? 'status-streaming' : 'status-disconnected'}`}>
              {streaming ? 'Streaming' : 'Stopped'}
            </span>
          </div>
        </div>
      </div>

      <div className="display-content">
        {/* Spectrum Plot with right-side controls */}
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 8 }}>
          <div className="spectrum-plot" style={{ flex: 1 }}>
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
          {/* Right-side vertical controls (Zoom and Range) */}
          <div style={{ width: 80, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, height: dimensions.height }}>
            {/* Zoom */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, flex: 1 }}>
              <div style={{ color: '#ccc', fontSize: 12 }}>Zoom</div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={zoomLevel}
                onChange={(e)=>setZoomLevel(parseFloat(e.target.value))}
                style={{ height: Math.max(80, Math.floor((dimensions.height - 40) / 2 - 20)), writingMode: 'bt-lr', WebkitAppearance: 'slider-vertical' }}
              />
              {/* Span label */}
              <div style={{ color: '#aaa', fontSize: 12 }}>
                {(() => {
                  if (!spectrumData?.frequencies || spectrumData.frequencies.length < 2) return 'Span: N/A'
                  const freqs = spectrumData.frequencies
                  const startIdx = Math.floor(viewRange.start * (freqs.length - 1))
                  const endIdx = Math.floor(viewRange.end * (freqs.length - 1))
                  const span = Math.abs(freqs[endIdx] - freqs[startIdx])
                  const fmt = (hz) => hz >= 1e6 ? `${(hz/1e6).toFixed(3)} MHz` : hz >= 1e3 ? `${(hz/1e3).toFixed(1)} kHz` : `${Math.round(hz)} Hz`
                  return `Span: ${fmt(span)}`
                })()}
              </div>
            </div>
            {/* dBFS Range (bottom control) */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, flex: 1 }}>
              <div style={{ color: '#ccc', fontSize: 12 }}>Range</div>
              <input
                type="range"
                min="-180"
                max="-40"
                step="1"
                value={dbfsBottom}
                onChange={(e)=>{ setDbfsBottom(parseFloat(e.target.value)); setAutoScale(false); }}
                style={{ height: Math.max(80, Math.floor((dimensions.height - 40) / 2 - 20)), writingMode: 'bt-lr', WebkitAppearance: 'slider-vertical' }}
                title="Bottom dBFS"
              />
              <div style={{ color: '#aaa', fontSize: 12 }}>{`Bottom: ${Math.round(dbfsBottom)} dBFS`}</div>
              <div style={{ color: '#aaa', fontSize: 11 }}>Top fixed: -30 dBFS</div>
            </div>
          </div>
        </div>

        {/* Waterfall Display */}
        <div className="waterfall-display">
          <h4 className="text-sm text-gray-300 mb-2">Waterfall</h4>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
            <label className="text-xs">
              Colormap
              <select value={waterfallColormap} onChange={(e)=>setWaterfallColormap(e.target.value)} className="input" style={{ marginLeft: 6, padding: '2px 4px' }}>
                <option value="viridis">Viridis</option>
                <option value="fire">Fire</option>
                <option value="grayscale">Grayscale</option>
              </select>
            </label>
            <label className="text-xs">
              Brightness
              <input type="range" min="0.5" max="2" step="0.05" value={waterfallBrightness} onChange={(e)=>setWaterfallBrightness(parseFloat(e.target.value))} style={{ width: 100, marginLeft: 6 }} />
            </label>
            <label className="text-xs">
              Contrast
              <input type="range" min="0.5" max="2" step="0.05" value={waterfallContrast} onChange={(e)=>setWaterfallContrast(parseFloat(e.target.value))} style={{ width: 100, marginLeft: 6 }} />
            </label>
            <label className="text-xs" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              Auto-Gain
              <input type="checkbox" checked={waterfallAutoGain} onChange={(e)=>setWaterfallAutoGain(e.target.checked)} />
            </label>
            <label className="text-xs" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              Rate
              <select value={waterfallRate} onChange={(e)=>setWaterfallRate(parseInt(e.target.value))} className="input" style={{ padding: '2px 4px' }}>
                <option value={1}>Every frame</option>
                <option value={2}>1/2</option>
                <option value={3}>1/3</option>
                <option value={5}>1/5</option>
              </select>
            </label>
            <button className="btn btn-secondary" onClick={()=>setWaterfallPaused(v=>!v)} style={{ padding: '4px 8px' }}>{waterfallPaused ? 'Resume' : 'Pause'}</button>
          </div>
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
            <div className="flex items-center gap-2" style={{ marginTop: 8, flexWrap: 'wrap' }}>
              <label className="text-gray-300 text-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={autoScale} onChange={(e)=>setAutoScale(e.target.checked)} /> Autoscale
              </label>
              {!autoScale && (
                <>
                  <label className="text-gray-300 text-sm">Min dB
                    <input type="number" value={userMinDb} onChange={(e)=>setUserMinDb(parseFloat(e.target.value)||-120)} className="input" style={{ width: 70, marginLeft: 6, padding: '2px 4px' }} />
                  </label>
                  <label className="text-gray-300 text-sm">Max dB
                    <input type="number" value={userMaxDb} onChange={(e)=>setUserMaxDb(parseFloat(e.target.value)||0)} className="input" style={{ width: 70, marginLeft: 6, padding: '2px 4px' }} />
                  </label>
                </>
              )}
              <label className="text-gray-300 text-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={smoothEnabled} onChange={(e)=>setSmoothEnabled(e.target.checked)} /> Smooth
              </label>
              {smoothEnabled && (
                <label className="text-gray-300 text-sm">Alpha
                  <input type="range" min="0.1" max="0.9" step="0.05" value={smoothAlpha} onChange={(e)=>setSmoothAlpha(parseFloat(e.target.value))} style={{ width: 100, marginLeft: 6 }} />
                </label>
              )}
              <label className="text-gray-300 text-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={avgEnabled} onChange={(e)=>{ setAvgEnabled(e.target.checked); if (!e.target.checked) avgBufferRef.current = null }} /> Avg
              </label>
              <label className="text-gray-300 text-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={peakEnabled} onChange={(e)=>{ setPeakEnabled(e.target.checked); if (!e.target.checked) peakBufferRef.current = null }} /> Peak
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function DigitGroup({ label, value, powers, onUp, onDown }) {
  const digits = String(value).split('')
  return (
    <div className="digit-group" style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      {digits.map((d, i) => (
        <div key={`${label}-${i}`} className="digit" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '0 4px', lineHeight: '12px', fontSize: 10, height: 16, minWidth: 18 }}
            onClick={() => onUp(powers[i])}
            onMouseDown={(e) => e.preventDefault()}
            title={`+${Math.pow(10, powers[i] || 0).toLocaleString()} Hz`}
          >▲</button>
          <div
            style={{ padding: '2px 4px', fontFamily: 'monospace', fontSize: 14, minWidth: 10, textAlign: 'center' }}
            title={`${label} digit`}
          >{d}</div>
          <button
            className="btn btn-secondary"
            style={{ padding: '0 4px', lineHeight: '12px', fontSize: 10, height: 16, minWidth: 18 }}
            onClick={() => onDown(powers[i])}
            onMouseDown={(e) => e.preventDefault()}
            title={`-${Math.pow(10, powers[i] || 0).toLocaleString()} Hz`}
          >▼</button>
        </div>
      ))}
      <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 4 }}>{label}</span>
    </div>
  )
}

export default SpectrumDisplay
