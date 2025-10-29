import React, { useState } from 'react'
import { sendAICommand } from '../api/aiClient'

export default function ChatPanel() {
	const [input, setInput] = useState('')
	const [messages, setMessages] = useState([])
	const [busy, setBusy] = useState(false)

	async function onSend(e) {
		e.preventDefault()
		if (!input.trim()) return
		const userText = input.trim()
		setInput('')
		setBusy(true)
		setMessages(m => [{ role: 'user', text: userText }, ...m])
		try {
			const res = await sendAICommand(userText)
			setMessages(m => [
				{ role: 'assistant', text: res?.intent?.explanation || 'Executed', raw: res },
				...m
			])
		} catch (err) {
			setMessages(m => [{ role: 'assistant', text: String(err) }, ...m])
		} finally {
			setBusy(false)
		}
	}

	return (
		<div style={{ padding: 16, display: 'grid', gap: 12 }}>
			<h2>AI Chat</h2>
			<form onSubmit={onSend} style={{ display: 'flex', gap: 8 }}>
				<input
					style={{ flex: 1 }}
					placeholder="Ask: tune to 104.1, scan FM, weather station..."
					value={input}
					onChange={e => setInput(e.target.value)}
				/>
				<button disabled={busy} type="submit">{busy ? '...' : 'Send'}</button>
			</form>
			<div style={{ display: 'grid', gap: 8 }}>
				{messages.map((m, idx) => (
					<div key={idx} style={{ padding: 8, border: '1px solid #ddd' }}>
						<div style={{ fontWeight: 600 }}>{m.role}</div>
						<div>{m.text}</div>
						{m.raw && <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(m.raw, null, 2)}</pre>}
					</div>
				))}
			</div>
		</div>
	)
}


