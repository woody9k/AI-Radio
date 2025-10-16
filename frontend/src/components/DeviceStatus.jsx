import React, { useState, useEffect } from 'react'

const DeviceStatus = ({ deviceConnected, deviceInfo, onConnect, onDisconnect }) => {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchDevices()
  }, [])

  const fetchDevices = async () => {
    try {
      const response = await fetch('/api/devices')
      const data = await response.json()
      
      if (data.success) {
        setDevices(data.devices || [])
      }
    } catch (error) {
      console.error('Error fetching devices:', error)
    }
  }

  const handleConnect = async (deviceIndex) => {
    setLoading(true)
    try {
      await onConnect(deviceIndex)
    } finally {
      setLoading(false)
    }
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
      <h3 className="text-lg font-bold mb-4">Device Status</h3>
      
      {!deviceConnected ? (
        <div>
          <p className="text-gray-300 mb-4">No device connected</p>
          
          {devices.length > 0 ? (
            <div>
              <p className="text-sm text-gray-300 mb-2">Available devices:</p>
              {devices.map((deviceIndex) => (
                <button
                  key={deviceIndex}
                  className="btn btn-primary w-full mb-2"
                  onClick={() => handleConnect(deviceIndex)}
                  disabled={loading}
                >
                  {loading ? 'Connecting...' : `Connect Device ${deviceIndex}`}
                </button>
              ))}
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-300 mb-2">No RTL-SDR devices found</p>
              <button
                className="btn btn-secondary w-full"
                onClick={fetchDevices}
              >
                Refresh
              </button>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <span className="status status-connected">Connected</span>
            <button
              className="btn btn-danger"
              onClick={onDisconnect}
            >
              Disconnect
            </button>
          </div>
          
          {deviceInfo && (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-300">Frequency:</span>
                <span className="text-white">{formatFrequency(deviceInfo.frequency)}</span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-300">Sample Rate:</span>
                <span className="text-white">{formatSampleRate(deviceInfo.sample_rate)}</span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-300">Gain:</span>
                <span className="text-white">{deviceInfo.gain}</span>
              </div>
              
              {deviceInfo.bandwidth && (
                <div className="flex justify-between">
                  <span className="text-gray-300">Bandwidth:</span>
                  <span className="text-white">{formatFrequency(deviceInfo.bandwidth)}</span>
                </div>
              )}
              
              <div className="flex justify-between">
                <span className="text-gray-300">Streaming:</span>
                <span className={deviceInfo.is_streaming ? 'status status-streaming' : 'text-gray-300'}>
                  {deviceInfo.is_streaming ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default DeviceStatus


