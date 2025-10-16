import React, { useState, useEffect } from 'react'
import { io } from 'socket.io-client'
import Controls from './components/Controls'
import SpectrumDisplay from './components/SpectrumDisplay'
import DeviceStatus from './components/DeviceStatus'
import AIPanel from './components/AIPanel'
import Presets from './components/Presets'
import './App.css'

function App() {
  const [socket, setSocket] = useState(null)
  const [connected, setConnected] = useState(false)
  const [deviceConnected, setDeviceConnected] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [spectrumData, setSpectrumData] = useState(null)
  const [waterfallData, setWaterfallData] = useState(null)
  const [deviceInfo, setDeviceInfo] = useState(null)
  const [aiDetections, setAiDetections] = useState([])

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

    setSocket(newSocket)

    return () => {
      newSocket.close()
    }
  }, [])

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

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI-Radio</h1>
        <div className="connection-status">
          <span className={`status ${connected ? 'status-connected' : 'status-disconnected'}`}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <div className="app-content">
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
          
          <Presets
            deviceConnected={deviceConnected}
            onApplyPreset={updateSettings}
          />
        </div>

        <div className="main-content">
          <SpectrumDisplay
            spectrumData={spectrumData}
            waterfallData={waterfallData}
            streaming={streaming}
          />
        </div>

        <div className="right-panel">
          <AIPanel
            detections={aiDetections}
            streaming={streaming}
          />
        </div>
      </div>
    </div>
  )
}

export default App
