import React, { useEffect, useState } from 'react'
import { getAISettings, saveAISettings } from '../api/aiClient'

export default function SettingsPage() {
	const [settings, setSettings] = useState({
		openai_api_key: '',
		openai_model: 'gpt-4o-mini',
		provider: 'openai',
		region: 'auto',
    auto_execute: false,
    theme: 'minimal',
	})
	const [saving, setSaving] = useState(false)
	const [message, setMessage] = useState('')

	useEffect(() => {
		getAISettings().then(res => {
			if (res.success) setSettings(prev => ({ ...prev, ...res.settings }))
      // Apply theme if present
      const theme = res?.settings?.theme || 'minimal'
      document.documentElement.setAttribute('data-theme', theme)
		})
	}, [])

	async function onSave(e) {
		e.preventDefault()
		setSaving(true)
		setMessage('')
		try {
			const res = await saveAISettings(settings)
			if (res.success) setMessage('Saved')
			else setMessage(res.error || 'Save failed')
		} finally {
			setSaving(false)
		}
	}

	return (
		<div style={{ padding: 16 }}>
			<h2>AI Settings</h2>
			<form onSubmit={onSave} style={{ maxWidth: 480, display: 'grid', gap: 12 }}>
        <label>
          Theme
          <select value={settings.theme}
            onChange={e => {
              const t = e.target.value
              setSettings({ ...settings, theme: t })
              document.documentElement.setAttribute('data-theme', t)
            }}>
            <option value="minimal">Minimal Mono</option>
            <option value="slate">Cool Slate</option>
            <option value="graphite">Graphite</option>
            <option value="forest">Forest Dim</option>
          </select>
        </label>
				<label>
					Provider
					<select value={settings.provider} onChange={e => setSettings({ ...settings, provider: e.target.value })}>
						<option value="openai">OpenAI</option>
					</select>
				</label>
				<label>
					OpenAI API Key
					<input type="password" value={settings.openai_api_key || ''}
						onChange={e => setSettings({ ...settings, openai_api_key: e.target.value })}
						placeholder="sk-..." />
				</label>
				<label>
					Model
					<input value={settings.openai_model}
						onChange={e => setSettings({ ...settings, openai_model: e.target.value })}/>
				</label>
				<label>
					Region
					<input value={settings.region}
						onChange={e => setSettings({ ...settings, region: e.target.value })}/>
				</label>
				<label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
					<input type="checkbox" checked={!!settings.auto_execute}
						onChange={e => setSettings({ ...settings, auto_execute: e.target.checked })}/>
					Auto-execute AI intents
				</label>
				<button disabled={saving} type="submit">{saving ? 'Saving...' : 'Save'}</button>
				{message && <div>{message}</div>}
			</form>
		</div>
	)
}


