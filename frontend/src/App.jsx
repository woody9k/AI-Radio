import React, { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import Controls from './components/Controls'
import SpectrumDisplay from './components/SpectrumDisplay'
import DeviceStatus from './components/DeviceStatus'
import AIPanel from './components/AIPanel'
import ChatPanel from './components/ChatPanel'
import SettingsPage from './components/SettingsPage'
import Presets from './components/Presets'
import SMeter from './components/SMeter'
import './App.css'
import { getAISettings } from './api/aiClient'

function App() {
  const [connected, setConnected] = useState(false)
  const [deviceConnected, setDeviceConnected] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [spectrumData, setSpectrumData] = useState(null)
  const [waterfallData, setWaterfallData] = useState(null)
  const [deviceInfo, setDeviceInfo] = useState(null)
  const [aiDetections, setAiDetections] = useState([])
  const [bookmarks, setBookmarks] = useState([])
  const [viewMode] = useState('beginner') // 'beginner' or 'advanced'
  const [activePane, setActivePane] = useState('radio') // 'radio' | 'chat' | 'settings' | 'analysis'
  const refreshingDevicesRef = useRef(false)

  useEffect(() => {
    // Initialize WebSocket connection
    const newSocket = io('http://localhost:5000')
    
    newSocket.on('connect', () => {
      console.log('Connected to server')
      setConnected(true)
    })

    newSocket.on('disconnect', () => {
      console.log('Disconnected from server')
      setConnected(false)
    })
    newSocket.io.on('reconnect', () => {
      console.log('Reconnected to server')
      setConnected(true)
    })

    newSocket.on('spectrum_data', (data) => {
      setSpectrumData(data)
      
      // Process AI detections from spectrum data
      if (data.signals && data.signals.length > 0) {
        setAiDetections(prev => {
          const newDetections = data.signals.map(signal => ({
            ...signal,
            timestamp: data.timestamp,
            type: 'signal_detected'
          }))
          
          // Keep only last 50 detections
          return [...newDetections, ...prev].slice(0, 50)
        })
      }
    })

    newSocket.on('waterfall_data', (data) => {
      setWaterfallData(data)
    })

    newSocket.on('status', (data) => {
      console.log('Status:', data.message)
    })

    newSocket.on('device_error', (data) => {
      console.error('Device error:', data.error)
      setDeviceConnected(false)
      setStreaming(false)
      alert(`Device error: ${data.error}. Please reconnect the device.`)
    })

    // Consolidated disconnect above; keep device state updates here
    newSocket.on('disconnect', () => {
      setDeviceConnected(false)
      setStreaming(false)
    })

    // no-op: we don't persist the socket in state

    // Health check every 5 seconds to detect backend restart (debounced)
    const healthCheckInterval = setInterval(async () => {
      try {
        const response = await fetch('/api/health')
        const data = await response.json()
        if (data.success) {
          // If backend says device is connected but frontend thinks it's not, refresh
          if (data.device_connected && !deviceConnected && !refreshingDevicesRef.current) {
            console.log('Backend has device but frontend does not - fetching devices')
            refreshingDevicesRef.current = true
            try { await fetchDevices() } finally { refreshingDevicesRef.current = false }
          }
          // If backend says not connected but frontend thinks it is, update
          if (!data.device_connected && deviceConnected) {
            console.log('Backend lost device - updating frontend state')
            setDeviceConnected(false)
            setStreaming(false)
          }
        }
      } catch (error) {
        // Suppress noisy logs during network changes/HMR
        // console.debug('Health check failed:', error)
      }
    }, 5000)

    return () => {
      newSocket.close()
      clearInterval(healthCheckInterval)
    }
  }, [])

  // Load theme on mount
  useEffect(() => {
    getAISettings().then(res => {
      const theme = res?.settings?.theme || 'minimal'
      document.documentElement.setAttribute('data-theme', theme)
    }).catch(() => {
      document.documentElement.setAttribute('data-theme', 'minimal')
    })
  }, [])

  const fetchDevices = async () => {
    try {
      const response = await fetch('/api/devices')
      const data = await response.json()
      if (data.success) {
        // If a device is already connected backend-side, reflect it in UI
        const connected = Object.values(data.device_info || {}).some(info => info.connected)
        setDeviceConnected(!!connected)
        if (connected) {
          // choose first connected device info
          const first = Object.values(data.device_info)[0]
          setDeviceInfo(first)
        }
      }
    } catch (e) {
      console.error('Failed to fetch devices:', e)
    }
  }

  const connectDevice = async (deviceIndex) => {
    try {
      const response = await fetch(`/api/devices/${deviceIndex}/connect`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setDeviceConnected(true)
        setDeviceInfo(data.device_info)
      } else {
        console.error('Failed to connect to device:', data.error)
      }
    } catch (error) {
      console.error('Error connecting to device:', error)
    }
  }

  const disconnectDevice = async () => {
    try {
      const response = await fetch('/api/devices/0/disconnect', {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setDeviceConnected(false)
        setDeviceInfo(null)
        setStreaming(false)
      }
    } catch (error) {
      console.error('Error disconnecting device:', error)
    }
  }

  const startStreaming = async () => {
    try {
      const response = await fetch('/api/stream/start', {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setStreaming(true)
      } else {
        console.error('Failed to start streaming:', data.error)
      }
    } catch (error) {
      console.error('Error starting stream:', error)
    }
  }

  const stopStreaming = async () => {
    try {
      const response = await fetch('/api/stream/stop', {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setStreaming(false)
      }
    } catch (error) {
      console.error('Error stopping stream:', error)
    }
  }

  const updateSettings = async (settings) => {
    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      })
      const data = await response.json()
      
      if (data.success) {
        setDeviceInfo(data.settings)
      } else {
        console.error('Failed to update settings:', data.error)
      }
    } catch (error) {
      console.error('Error updating settings:', error)
    }
  }

  const tuneToFrequency = async (frequency, bandwidth = null) => {
    const settings = { frequency }
    if (bandwidth) {
      settings.bandwidth = bandwidth
    }
    await updateSettings(settings)
  }

  const listenToSignal = async (signal) => {
    try {
      const response = await fetch('/api/tune_signal', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          frequency: signal.frequency,
          bandwidth: signal.bandwidth,
          modulation: signal.modulation || signal.mod || 'FM'
        })
      })
      
      const data = await response.json()
      
      if (data.success) {
        console.log('Tuned to signal and started audio')
      } else {
        alert(`Failed to listen to signal: ${data.error}`)
      }
    } catch (error) {
      console.error('Error listening to signal:', error)
      alert('Error listening to signal')
    }
  }

  const bookmarkSignal = (signal) => {
    setBookmarks(prev => {
      const key = `${Math.round(signal.frequency)}-${signal.bandwidth || 0}`
      if (prev.find(b => b.key === key)) return prev
      return [{ key, ...signal, savedAt: Date.now() }, ...prev].slice(0, 50)
    })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI-Radio</h1>
        <div className="connection-status">
          <span className={`status ${connected ? 'status-connected' : 'status-disconnected'}`}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          <span style={{ marginLeft: 12, fontSize: 12, opacity: 0.8 }}>Bookmarks: {bookmarks.length}</span>
        </div>
      </header>

      <div className="top-nav">
        <button onClick={() => setActivePane('radio')}>Radio</button>
        <button onClick={() => setActivePane('chat')}>AI Chat</button>
        <button onClick={() => setActivePane('analysis')}>Analysis</button>
        <button onClick={() => setActivePane('settings')}>Settings</button>
      </div>

      <div className="app-content">
        {activePane === 'chat' && (
          <div className="main-content" style={{ width: '100%' }}>
            <ChatPanel />
          </div>
        )}
        {activePane === 'analysis' && (
          <div className="main-content" style={{ width: '100%' }}>
            <AIPanel
              detections={aiDetections}
              streaming={streaming}
              viewMode={viewMode}
              onListenToSignal={listenToSignal}
            />
          </div>
        )}
        {activePane === 'settings' && (
          <div className="main-content" style={{ width: '100%' }}>
            <SettingsPage />
          </div>
        )}
        {activePane === 'radio' && (
        <>
        <div className="left-panel">
          <DeviceStatus 
            deviceConnected={deviceConnected}
            deviceInfo={deviceInfo}
            onConnect={connectDevice}
            onDisconnect={disconnectDevice}
          />
          
          <Controls
            deviceConnected={deviceConnected}
            streaming={streaming}
            deviceInfo={deviceInfo}
            onStartStreaming={startStreaming}
            onStopStreaming={stopStreaming}
            onUpdateSettings={updateSettings}
          />
        </div>

        <div className="main-content">
          <SpectrumDisplay
            spectrumData={spectrumData}
            waterfallData={waterfallData}
            streaming={streaming}
            onTuneToFrequency={tuneToFrequency}
            currentFrequency={deviceInfo?.frequency}
            currentBandwidth={deviceInfo?.bandwidth}
            onListenToSignal={listenToSignal}
            onBookmarkSignal={bookmarkSignal}
          />
          <SMeter spectrumData={spectrumData} tunedFrequency={deviceInfo?.frequency} />

          {/* Move Presets here below the SMeter */}
          <div style={{ padding: 12 }}>
            <Presets
              deviceConnected={deviceConnected}
              onApplyPreset={updateSettings}
            />
          </div>
        </div>

        <div className="right-panel">
          <ChatPanel />
        </div>
        </>
        )}
      </div>
    </div>
  )
}

export default App
