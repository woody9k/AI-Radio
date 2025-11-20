import React, { useState, useEffect } from 'react'

const SignalDatabase = () => {
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({
    freqMin: '',
    freqMax: '',
    category: ''
  })
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchSignals()
    fetchStats()
  }, [])

  const fetchSignals = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.freqMin) params.append('freq_min', filters.freqMin)
      if (filters.freqMax) params.append('freq_max', filters.freqMax)
      if (filters.category) params.append('category', filters.category)
      params.append('limit', '100')

      const response = await fetch(`/api/signals?${params}`)
      const data = await response.json()
      if (data.success) {
        setSignals(data.signals || [])
      }
    } catch (error) {
      console.error('Error fetching signals:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/signals/stats')
      const data = await response.json()
      if (data.success) {
        setStats(data)
      }
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      fetchSignals()
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/signals/search?q=${encodeURIComponent(searchTerm)}`)
      const data = await response.json()
      if (data.success) {
        setSignals(data.signals || [])
      }
    } catch (error) {
      console.error('Error searching signals:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatFrequency = (freq) => {
    if (!freq) return 'N/A'
    if (freq >= 1e9) return `${(freq / 1e9).toFixed(3)} GHz`
    if (freq >= 1e6) return `${(freq / 1e6).toFixed(3)} MHz`
    if (freq >= 1e3) return `${(freq / 1e3).toFixed(3)} kHz`
    return `${freq.toFixed(0)} Hz`
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className="signal-database" style={{ padding: '12px' }}>
      <h3 style={{ marginTop: 0 }}>Signal Database</h3>

      {stats && (
        <div style={{ padding: '8px', background: '#1a1a1a', borderRadius: '4px', marginBottom: '12px', fontSize: '12px' }}>
          <div><strong>Total Signals:</strong> {stats.total_signals?.toLocaleString() || 0}</div>
          {stats.by_category && Object.keys(stats.by_category).length > 0 && (
            <div style={{ marginTop: '4px' }}>
              <strong>By Category:</strong>
              {Object.entries(stats.by_category).map(([cat, count]) => (
                <span key={cat} style={{ marginLeft: '8px' }}>
                  {cat}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
            placeholder="Search by description or category..."
            className="input"
            style={{ flex: 1, padding: '4px 6px', fontSize: '12px' }}
          />
          <button className="btn btn-primary" onClick={handleSearch} style={{ padding: '4px 12px' }}>
            Search
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
          <input
            type="number"
            value={filters.freqMin}
            onChange={(e) => setFilters({ ...filters, freqMin: e.target.value })}
            placeholder="Min Freq (Hz)"
            className="input"
            style={{ width: '120px', padding: '4px 6px', fontSize: '12px' }}
          />
          <input
            type="number"
            value={filters.freqMax}
            onChange={(e) => setFilters({ ...filters, freqMax: e.target.value })}
            placeholder="Max Freq (Hz)"
            className="input"
            style={{ width: '120px', padding: '4px 6px', fontSize: '12px' }}
          />
          <select
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            className="input"
            style={{ padding: '4px 6px', fontSize: '12px' }}
          >
            <option value="">All Categories</option>
            <option value="aviation">Aviation</option>
            <option value="fm_radio">FM Radio</option>
            <option value="cb_radio">CB Radio</option>
            <option value="ham_2m">Ham 2m</option>
            <option value="ham_70cm">Ham 70cm</option>
            <option value="weather">Weather</option>
            <option value="unknown">Unknown</option>
          </select>
          <button className="btn btn-secondary" onClick={fetchSignals} style={{ padding: '4px 12px' }}>
            Filter
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '12px', textAlign: 'center', color: '#999' }}>
          Loading...
        </div>
      )}

      {!loading && signals.length === 0 && (
        <div style={{ padding: '12px', textAlign: 'center', color: '#999', fontSize: '12px' }}>
          No signals found
        </div>
      )}

      {!loading && signals.length > 0 && (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {signals.map((signal) => (
            <div
              key={signal.id}
              style={{
                padding: '8px',
                background: '#1a1a1a',
                borderRadius: '4px',
                marginBottom: '8px',
                fontSize: '12px'
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                {formatFrequency(signal.frequency)}
                {signal.category && (
                  <span style={{ marginLeft: '8px', color: '#3b82f6' }}>
                    [{signal.category}]
                  </span>
                )}
              </div>
              {signal.description && (
                <div style={{ color: '#999', marginBottom: '4px' }}>{signal.description}</div>
              )}
              <div style={{ color: '#999', fontSize: '11px' }}>
                Power: {signal.power?.toFixed(1) || 'N/A'} dB • 
                SNR: {signal.snr?.toFixed(1) || 'N/A'} dB • 
                Confidence: {signal.confidence ? (signal.confidence * 100).toFixed(0) + '%' : 'N/A'} • 
                {formatDate(signal.timestamp)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SignalDatabase

