import React, { useState, useEffect, useRef } from 'react'

const AudioPlayer = ({ socket, deviceConnected }) => {
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [volume, setVolume] = useState(0.8)
  const [muted, setMuted] = useState(false)
  const [audioMode, setAudioMode] = useState('FM')
  const [vuLevel, setVuLevel] = useState(0)
  
  const audioContextRef = useRef(null)
  const gainNodeRef = useRef(null)
  const audioBufferQueueRef = useRef([])
  const nextPlayTimeRef = useRef(0)
  const audioSampleRateRef = useRef(48000)
  
  useEffect(() => {
    if (!socket) return
    
    // Initialize Web Audio API
    const AudioContext = window.AudioContext || window.webkitAudioContext
    audioContextRef.current = new AudioContext()
    gainNodeRef.current = audioContextRef.current.createGain()
    gainNodeRef.current.connect(audioContextRef.current.destination)
    gainNodeRef.current.gain.value = volume
    
    // Listen for audio samples from backend
    socket.on('audio_samples', handleAudioSamples)
    
    return () => {
      socket.off('audio_samples', handleAudioSamples)
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [socket])
  
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = muted ? 0 : volume
    }
  }, [volume, muted])
  
  const handleAudioSamples = (data) => {
    if (!audioContextRef.current || !audioPlaying) return
    
    try {
      const { samples, sample_rate, mode } = data
      audioSampleRateRef.current = sample_rate
      
      // Create audio buffer
      const audioBuffer = audioContextRef.current.createBuffer(
        1, // mono
        samples.length,
        sample_rate
      )
      
      // Fill buffer with samples
      const channelData = audioBuffer.getChannelData(0)
      for (let i = 0; i < samples.length; i++) {
        channelData[i] = samples[i]
      }
      
      // Calculate VU level (RMS)
      let sum = 0
      for (let i = 0; i < samples.length; i++) {
        sum += samples[i] * samples[i]
      }
      const rms = Math.sqrt(sum / samples.length)
      setVuLevel(Math.min(100, rms * 200)) // Scale to 0-100
      
      // Play audio buffer
      playAudioBuffer(audioBuffer)
      
    } catch (error) {
      console.error('Error handling audio samples:', error)
    }
  }
  
  const playAudioBuffer = (audioBuffer) => {
    const source = audioContextRef.current.createBufferSource()
    source.buffer = audioBuffer
    source.connect(gainNodeRef.current)
    
    // Schedule playback for continuous audio
    const currentTime = audioContextRef.current.currentTime
    if (nextPlayTimeRef.current < currentTime) {
      nextPlayTimeRef.current = currentTime
    }
    
    source.start(nextPlayTimeRef.current)
    nextPlayTimeRef.current += audioBuffer.duration
  }
  
  const handleStartAudio = async () => {
    if (!deviceConnected) {
      alert('Please connect a device first')
      return
    }
    
    try {
      // Resume audio context if suspended
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume()
      }
      
      // Start audio streaming from backend
      const response = await fetch('/api/audio/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: audioMode })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setAudioPlaying(true)
        setAudioMode(data.mode)
        nextPlayTimeRef.current = audioContextRef.current.currentTime
      } else {
        alert(`Failed to start audio: ${data.error}`)
      }
    } catch (error) {
      console.error('Error starting audio:', error)
      alert('Error starting audio')
    }
  }
  
  const handleStopAudio = async () => {
    try {
      const response = await fetch('/api/audio/stop', {
        method: 'POST'
      })
      
      const data = await response.json()
      
      if (data.success) {
        setAudioPlaying(false)
        setVuLevel(0)
      } else {
        alert(`Failed to stop audio: ${data.error}`)
      }
    } catch (error) {
      console.error('Error stopping audio:', error)
      alert('Error stopping audio')
    }
  }
  
  return (
    <div className="audio-player">
      <h3 className="text-sm font-bold mb-2">Audio</h3>
      
      <div className="audio-controls space-y-2">
        {/* Mode Selector */}
        <div className="flex gap-2">
          <button
            className={`btn text-xs flex-1 ${audioMode === 'FM' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setAudioMode('FM')}
            disabled={audioPlaying}
          >
            FM
          </button>
          <button
            className={`btn text-xs flex-1 ${audioMode === 'AM' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setAudioMode('AM')}
            disabled={audioPlaying}
          >
            AM
          </button>
        </div>
        
        {/* Play/Stop Button */}
        <div className="flex gap-2">
          {!audioPlaying ? (
            <button
              className="btn btn-success text-xs flex-1"
              onClick={handleStartAudio}
              disabled={!deviceConnected}
            >
              ▶ Listen
            </button>
          ) : (
            <button
              className="btn btn-danger text-xs flex-1"
              onClick={handleStopAudio}
            >
              ⏹ Stop
            </button>
          )}
          
          {/* Mute Button */}
          <button
            className="btn btn-secondary text-xs"
            onClick={() => setMuted(!muted)}
            disabled={!audioPlaying}
            style={{ width: '40px' }}
          >
            {muted ? '🔇' : '🔊'}
          </button>
        </div>
        
        {/* Volume Control */}
        <div>
          <label className="block text-xs text-gray-300 mb-1">
            Volume: {Math.round(volume * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="w-full"
            disabled={!audioPlaying}
          />
        </div>
        
        {/* VU Meter */}
        {audioPlaying && (
          <div>
            <label className="block text-xs text-gray-300 mb-1">
              Signal Level
            </label>
            <div className="vu-meter">
              <div 
                className="vu-bar"
                style={{ 
                  width: `${vuLevel}%`,
                  backgroundColor: vuLevel > 80 ? '#ef4444' : vuLevel > 50 ? '#f59e0b' : '#10b981'
                }}
              />
            </div>
          </div>
        )}
        
        {/* Status */}
        <div className="text-xs text-gray-400 text-center">
          {audioPlaying ? (
            <span className="text-green-400">● Listening ({audioMode})</span>
          ) : (
            <span>Audio Off</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default AudioPlayer

