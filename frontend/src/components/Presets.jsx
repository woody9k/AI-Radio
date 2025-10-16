import React, { useState, useEffect } from 'react'

const Presets = ({ deviceConnected, onApplyPreset }) => {
  const [presets, setPresets] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [favorites, setFavorites] = useState([])
  const [collapsedCategories, setCollapsedCategories] = useState({})
  const [newPreset, setNewPreset] = useState({
    name: '',
    description: '',
    frequency: '',
    sample_rate: 2048000,
    gain: 'auto',
    bandwidth: '',
    category: 'Custom',
    tips: []
  })

  useEffect(() => {
    fetchPresets()
    loadFavorites()
  }, [selectedCategory, searchQuery])

  const loadFavorites = () => {
    const saved = localStorage.getItem('preset_favorites')
    if (saved) {
      setFavorites(JSON.parse(saved))
    }
  }

  const saveFavorites = (newFavs) => {
    setFavorites(newFavs)
    localStorage.setItem('preset_favorites', JSON.stringify(newFavs))
  }

  const toggleFavorite = (presetName) => {
    const newFavs = favorites.includes(presetName)
      ? favorites.filter(f => f !== presetName)
      : [...favorites, presetName]
    saveFavorites(newFavs)
  }

  const toggleCategory = (category) => {
    setCollapsedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }))
  }

  const fetchPresets = async () => {
    setLoading(true)
    try {
      let url = '/api/presets'
      const params = new URLSearchParams()
      
      if (selectedCategory) {
        params.append('category', selectedCategory)
      }
      if (searchQuery) {
        params.append('search', searchQuery)
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`
      }
      
      const response = await fetch(url)
      const data = await response.json()
      
      if (data.success) {
        setPresets(data.presets)
        setCategories(data.categories)
      }
    } catch (error) {
      console.error('Error fetching presets:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApplyPreset = async (presetName) => {
    if (!deviceConnected) {
      alert('Please connect a device first')
      return
    }

    try {
      const response = await fetch(`/api/presets/${encodeURIComponent(presetName)}/apply`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        onApplyPreset(data.device_info)
        fetchPresets() // Refresh to update last_used
      } else {
        alert(`Failed to apply preset: ${data.error}`)
      }
    } catch (error) {
      console.error('Error applying preset:', error)
      alert('Error applying preset')
    }
  }

  const handleCreatePreset = async (e) => {
    e.preventDefault()
    
    try {
      const response = await fetch('/api/presets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newPreset)
      })
      const data = await response.json()
      
      if (data.success) {
        setShowCreateForm(false)
        setNewPreset({
          name: '',
          description: '',
          frequency: '',
          sample_rate: 2048000,
          gain: 'auto',
          bandwidth: '',
          category: 'Custom',
          tips: []
        })
        fetchPresets()
        alert('Preset created successfully!')
      } else {
        alert(`Failed to create preset: ${data.error}`)
      }
    } catch (error) {
      console.error('Error creating preset:', error)
      alert('Error creating preset')
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

  const renderPresetCard = (preset, index) => (
    <div key={index} className="bg-gray-800 p-3 rounded text-xs">
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="text-white font-medium">{preset.name}</h4>
            <button
              className="text-lg hover:scale-125 transition-transform"
              onClick={() => toggleFavorite(preset.name)}
              title={favorites.includes(preset.name) ? 'Remove from favorites' : 'Add to favorites'}
            >
              {favorites.includes(preset.name) ? '⭐' : '☆'}
            </button>
          </div>
          <p className="text-gray-300">{preset.description}</p>
        </div>
        <span className="bg-gray-700 px-2 py-1 rounded text-xs">
          {preset.category}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-2 mb-2 text-gray-300">
        <div>Freq: {formatFrequency(preset.frequency)}</div>
        <div>Rate: {formatSampleRate(preset.sample_rate)}</div>
        <div>Gain: {preset.gain}</div>
        {preset.bandwidth && <div>BW: {formatFrequency(preset.bandwidth)}</div>}
      </div>
      
      {preset.tips && preset.tips.length > 0 && (
        <div className="mb-2">
          <p className="text-gray-400 text-xs mb-1">Tips:</p>
          <ul className="text-gray-400 text-xs space-y-1">
            {preset.tips.slice(0, 2).map((tip, tipIndex) => (
              <li key={tipIndex} className="list-disc list-inside">
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="flex justify-between items-center">
        <div className="text-gray-500 text-xs">
          <span>Used {preset.usage_count} times</span>
          {preset.last_used && (
            <span className="ml-2">• {new Date(preset.last_used).toLocaleDateString()}</span>
          )}
        </div>
        <button
          className="btn btn-primary text-xs"
          onClick={() => handleApplyPreset(preset.name)}
          disabled={!deviceConnected}
        >
          Apply
        </button>
      </div>
    </div>
  )

  // Get favorites
  const favoritePresets = presets.filter(p => favorites.includes(p.name))
  
  // Get recent (last 5 used)
  const recentPresets = [...presets]
    .filter(p => p.last_used)
    .sort((a, b) => new Date(b.last_used) - new Date(a.last_used))
    .slice(0, 5)
  
  // Group by category
  const presetsByCategory = {}
  presets.forEach(preset => {
    if (!presetsByCategory[preset.category]) {
      presetsByCategory[preset.category] = []
    }
    presetsByCategory[preset.category].push(preset)
  })

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">Presets</h3>
        <button
          className="btn btn-primary text-xs"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : 'Create'}
        </button>
      </div>

      {/* Create Preset Form */}
      {showCreateForm && (
        <form onSubmit={handleCreatePreset} className="mb-4 p-3 bg-gray-800 rounded">
          <h4 className="text-sm font-bold mb-2">Create Custom Preset</h4>
          
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Preset Name"
              value={newPreset.name}
              onChange={(e) => setNewPreset({...newPreset, name: e.target.value})}
              className="input w-full text-xs"
              required
            />
            
            <input
              type="text"
              placeholder="Description"
              value={newPreset.description}
              onChange={(e) => setNewPreset({...newPreset, description: e.target.value})}
              className="input w-full text-xs"
              required
            />
            
            <input
              type="number"
              placeholder="Frequency (Hz)"
              value={newPreset.frequency}
              onChange={(e) => setNewPreset({...newPreset, frequency: parseFloat(e.target.value)})}
              className="input w-full text-xs"
              required
            />
            
            <select
              value={newPreset.sample_rate}
              onChange={(e) => setNewPreset({...newPreset, sample_rate: parseFloat(e.target.value)})}
              className="input w-full text-xs"
            >
              <option value={250000}>250 kS/s</option>
              <option value={500000}>500 kS/s</option>
              <option value={1024000}>1.024 MS/s</option>
              <option value={1536000}>1.536 MS/s</option>
              <option value={2048000}>2.048 MS/s</option>
              <option value={2560000}>2.56 MS/s</option>
              <option value={3072000}>3.072 MS/s</option>
            </select>
            
            <select
              value={newPreset.gain}
              onChange={(e) => setNewPreset({...newPreset, gain: e.target.value})}
              className="input w-full text-xs"
            >
              <option value="auto">Auto</option>
              <option value="0">0 dB</option>
              <option value="9.9">9.9 dB</option>
              <option value="14.4">14.4 dB</option>
              <option value="19.7">19.7 dB</option>
              <option value="24.3">24.3 dB</option>
              <option value="29.7">29.7 dB</option>
              <option value="34.8">34.8 dB</option>
              <option value="42.1">42.1 dB</option>
              <option value="43.9">43.9 dB</option>
            </select>
            
            <input
              type="number"
              placeholder="Bandwidth (Hz, optional)"
              value={newPreset.bandwidth}
              onChange={(e) => setNewPreset({...newPreset, bandwidth: e.target.value})}
              className="input w-full text-xs"
            />
            
            <select
              value={newPreset.category}
              onChange={(e) => setNewPreset({...newPreset, category: e.target.value})}
              className="input w-full text-xs"
            >
              <option value="Custom">Custom</option>
              <option value="Broadcast">Broadcast</option>
              <option value="Aviation">Aviation</option>
              <option value="Amateur Radio">Amateur Radio</option>
              <option value="Marine">Marine</option>
              <option value="Public Safety">Public Safety</option>
              <option value="Satellites">Satellites</option>
            </select>
            
            <div className="flex gap-2">
              <button type="submit" className="btn btn-success text-xs flex-1">
                Create
              </button>
              <button 
                type="button" 
                className="btn btn-secondary text-xs flex-1"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search presets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input w-full text-xs"
        />
      </div>

      {/* Presets List */}
      {loading ? (
        <p className="text-gray-300 text-sm">Loading presets...</p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {/* Favorites Section */}
          {favoritePresets.length > 0 && (
            <div>
              <button
                className="flex items-center justify-between w-full text-sm font-bold text-yellow-400 mb-2 hover:text-yellow-300"
                onClick={() => toggleCategory('Favorites')}
              >
                <span>⭐ Favorites ({favoritePresets.length})</span>
                <span>{collapsedCategories['Favorites'] ? '▼' : '▲'}</span>
              </button>
              {!collapsedCategories['Favorites'] && (
                <div className="space-y-2 mb-3">
                  {favoritePresets.map((preset, idx) => renderPresetCard(preset, `fav-${idx}`))}
                </div>
              )}
            </div>
          )}

          {/* Recent Section */}
          {recentPresets.length > 0 && (
            <div>
              <button
                className="flex items-center justify-between w-full text-sm font-bold text-blue-400 mb-2 hover:text-blue-300"
                onClick={() => toggleCategory('Recent')}
              >
                <span>🕐 Recent ({recentPresets.length})</span>
                <span>{collapsedCategories['Recent'] ? '▼' : '▲'}</span>
              </button>
              {!collapsedCategories['Recent'] && (
                <div className="space-y-2 mb-3">
                  {recentPresets.map((preset, idx) => renderPresetCard(preset, `recent-${idx}`))}
                </div>
              )}
            </div>
          )}

          {/* Categories */}
          {Object.keys(presetsByCategory).sort().map(category => (
            <div key={category}>
              <button
                className="flex items-center justify-between w-full text-sm font-bold text-gray-300 mb-2 hover:text-white"
                onClick={() => toggleCategory(category)}
              >
                <span>{category} ({presetsByCategory[category].length})</span>
                <span>{collapsedCategories[category] ? '▼' : '▲'}</span>
              </button>
              {!collapsedCategories[category] && (
                <div className="space-y-2 mb-3">
                  {presetsByCategory[category].map((preset, idx) => renderPresetCard(preset, `${category}-${idx}`))}
                </div>
              )}
            </div>
          ))}

          {presets.length === 0 && (
            <p className="text-gray-300 text-sm">No presets found</p>
          )}
        </div>
      )}
    </div>
  )
}

export default Presets
