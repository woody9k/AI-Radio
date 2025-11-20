import React, { useState, useEffect } from 'react'

const RecordingPanel = ({ deviceConnected, deviceInfo }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingStatus, setRecordingStatus] = useState(null)
  const [recordings, setRecordings] = useState([])
  const [description, setDescription] = useState('')

  useEffect(() => {
    fetchRecordings()
    const interval = setInterval(() => {
      if (isRecording) {
        fetchRecordingStatus()
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [isRecording])

  const fetchRecordings = async () => {
    try {
      const response = await fetch('/api/recording/list')
      const data = await response.json()
      if (data.success) {
        setRecordings(data.recordings || [])
      }
    } catch (error) {
      console.error('Error fetching recordings:', error)
    }
  }

  const fetchRecordingStatus = async () => {
    try {
      const response = await fetch('/api/recording/status')
      const data = await response.json()
      if (data.success && data.status) {
        setRecordingStatus(data.status)
        setIsRecording(data.status.is_recording)
      }
    } catch (error) {
      console.error('Error fetching recording status:', error)
    }
  }

  const startRecording = async () => {
    try {
      const response = await fetch('/api/recording/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description })
      })
      const data = await response.json()
      if (data.success) {
        setIsRecording(true)
        setRecordingStatus(data.metadata)
        setDescription('')
      } else {
        alert(`Failed to start recording: ${data.error}`)
      }
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Error starting recording')
    }
  }

  const stopRecording = async () => {
    try {
      const response = await fetch('/api/recording/stop', {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        setIsRecording(false)
        setRecordingStatus(null)
        fetchRecordings()
      } else {
        alert(`Failed to stop recording: ${data.error}`)
      }
    } catch (error) {
      console.error('Error stopping recording:', error)
      alert('Error stopping recording')
    }
  }

  const deleteRecording = async (filename) => {
    if (!confirm(`Delete recording ${filename}?`)) {
      return
    }

    try {
      const response = await fetch(`/api/recording/${filename}/delete`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.success) {
        fetchRecordings()
      } else {
        alert(`Failed to delete recording: ${data.error}`)
      }
    } catch (error) {
      console.error('Error deleting recording:', error)
      alert('Error deleting recording')
    }
  }

  const downloadRecording = (filename) => {
    window.open(`/api/recording/${filename}/download`, '_blank')
  }

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B'
    const kb = bytes / 1024
    const mb = kb / 1024
    if (mb >= 1) {
      return `${mb.toFixed(2)} MB`
    }
    return `${kb.toFixed(2)} KB`
  }

  return (
    <div className="recording-panel" style={{ padding: '12px' }}>
      <h3 style={{ marginTop: 0 }}>Recording</h3>

      {!deviceConnected && (
        <div style={{ padding: '8px', background: '#f44336', borderRadius: '4px', marginBottom: '12px' }}>
          Device not connected
        </div>
      )}

      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px' }}>
          Description (optional)
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Recording description"
          disabled={isRecording}
          className="input"
          style={{ width: '100%', padding: '4px 6px', fontSize: '12px' }}
        />
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {!isRecording ? (
          <button
            className="btn btn-primary"
            onClick={startRecording}
            disabled={!deviceConnected}
            style={{ flex: 1 }}
          >
            Start Recording
          </button>
        ) : (
          <button
            className="btn btn-secondary"
            onClick={stopRecording}
            style={{ flex: 1, background: '#f44336' }}
          >
            Stop Recording
          </button>
        )}
      </div>

      {isRecording && recordingStatus && (
        <div style={{ padding: '8px', background: '#1a1a1a', borderRadius: '4px', marginBottom: '12px', fontSize: '12px' }}>
          <div><strong>Recording:</strong> {recordingStatus.filename}</div>
          <div><strong>Duration:</strong> {formatDuration(recordingStatus.duration)}</div>
          <div><strong>Samples:</strong> {recordingStatus.samples_written?.toLocaleString() || 0}</div>
          {recordingStatus.frequency && (
            <div><strong>Frequency:</strong> {(recordingStatus.frequency / 1e6).toFixed(3)} MHz</div>
          )}
        </div>
      )}

      <div style={{ marginTop: '16px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '8px' }}>Recordings</h4>
        {recordings.length === 0 ? (
          <div style={{ padding: '12px', textAlign: 'center', color: '#999', fontSize: '12px' }}>
            No recordings yet
          </div>
        ) : (
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {recordings.map((recording) => (
              <div
                key={recording.filename}
                style={{
                  padding: '8px',
                  background: '#1a1a1a',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  fontSize: '12px'
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                  {recording.filename}
                </div>
                {recording.description && (
                  <div style={{ color: '#999', marginBottom: '4px' }}>{recording.description}</div>
                )}
                <div style={{ color: '#999', marginBottom: '4px' }}>
                  {new Date(recording.start_time).toLocaleString()} • {formatDuration(recording.duration)} • {formatFileSize(recording.file_size)}
                </div>
                <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => downloadRecording(recording.filename)}
                    style={{ padding: '2px 8px', fontSize: '11px' }}
                  >
                    Download
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => deleteRecording(recording.filename)}
                    style={{ padding: '2px 8px', fontSize: '11px', background: '#f44336' }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default RecordingPanel

