import React, { useState, useEffect, useRef } from 'react'
import { sendAICommand } from '../api/aiClient'

export default function ChatPanel() {
	const [input, setInput] = useState('')
	const [messages, setMessages] = useState([])
	const [busy, setBusy] = useState(false)
	const [expandedMessages, setExpandedMessages] = useState(new Set())
	const messagesEndRef = useRef(null)
	const containerRef = useRef(null)

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
	}

	useEffect(() => {
		scrollToBottom()
	}, [messages])

	async function onSend(e) {
		e.preventDefault()
		if (!input.trim() || busy) return
		const userText = input.trim()
		setInput('')
		setBusy(true)
		
		const userMessage = {
			role: 'user',
			text: userText,
			timestamp: new Date()
		}
		setMessages(m => [...m, userMessage])
		
		try {
			const res = await sendAICommand(userText)
			const assistantMessage = {
				role: 'assistant',
				text: res?.intent?.explanation || res?.error || 'Command executed',
				raw: res,
				success: res?.success !== false,
				timestamp: new Date()
			}
			setMessages(m => [...m, assistantMessage])
		} catch (err) {
			const errorMessage = {
				role: 'assistant',
				text: `Error: ${err.message || String(err)}`,
				success: false,
				timestamp: new Date()
			}
			setMessages(m => [...m, errorMessage])
		} finally {
			setBusy(false)
		}
	}

	const toggleExpand = (index) => {
		setExpandedMessages(prev => {
			const next = new Set(prev)
			if (next.has(index)) {
				next.delete(index)
			} else {
				next.add(index)
			}
			return next
		})
	}

	const formatTimestamp = (date) => {
		if (!date) return ''
		return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
	}

	return (
		<div 
			ref={containerRef}
			style={{ 
				display: 'flex', 
				flexDirection: 'column', 
				height: '100%',
				maxHeight: '100%',
				overflow: 'hidden'
			}}
		>
			<div style={{ 
				padding: '12px 16px', 
				borderBottom: '1px solid #333',
				flexShrink: 0
			}}>
				<h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#e5e7eb' }}>
					AI Assistant
				</h3>
			</div>
			
			<div style={{ 
				flex: 1, 
				overflowY: 'auto',
				padding: '16px',
				display: 'flex',
				flexDirection: 'column',
				gap: '12px'
			}}>
				{messages.length === 0 && (
					<div style={{ 
						color: '#9ca3af', 
						fontSize: '13px', 
						textAlign: 'center',
						padding: '24px',
						fontStyle: 'italic'
					}}>
						Ask me to tune to a frequency, scan for stations, or help with radio operations.
					</div>
				)}
				{messages.map((m, idx) => (
					<div 
						key={idx} 
						style={{ 
							display: 'flex',
							flexDirection: 'column',
							gap: '4px',
							maxWidth: '100%'
						}}
					>
						<div style={{
							display: 'flex',
							alignItems: 'flex-start',
							gap: '8px'
						}}>
							<div style={{
								width: '24px',
								height: '24px',
								borderRadius: '12px',
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								fontSize: '11px',
								fontWeight: 600,
								flexShrink: 0,
								backgroundColor: m.role === 'user' ? '#3b82f6' : 
									m.success === false ? '#ef4444' : '#10b981',
								color: 'white'
							}}>
								{m.role === 'user' ? 'U' : 'AI'}
							</div>
							<div style={{ flex: 1, minWidth: 0 }}>
								<div style={{
									backgroundColor: m.role === 'user' ? '#1f2937' : 
										m.success === false ? 'rgba(239, 68, 68, 0.1)' : '#1f2937',
									border: `1px solid ${m.success === false ? '#ef4444' : '#374151'}`,
									borderRadius: '8px',
									padding: '10px 12px',
									color: '#e5e7eb',
									fontSize: '13px',
									lineHeight: '1.5',
									whiteSpace: 'pre-wrap',
									wordBreak: 'break-word'
								}}>
									{m.text}
								</div>
								{m.raw && (
									<div style={{ marginTop: '4px' }}>
										<button
											onClick={() => toggleExpand(idx)}
											style={{
												background: 'transparent',
												border: 'none',
												color: '#9ca3af',
												cursor: 'pointer',
												fontSize: '11px',
												padding: '4px 0',
												textDecoration: 'underline'
											}}
										>
											{expandedMessages.has(idx) ? 'Hide details' : 'Show details'}
										</button>
										{expandedMessages.has(idx) && (
											<pre style={{
												marginTop: '8px',
												padding: '8px',
												backgroundColor: '#0a0a0a',
												border: '1px solid #333',
												borderRadius: '4px',
												fontSize: '11px',
												color: '#9ca3af',
												overflow: 'auto',
												maxHeight: '200px',
												whiteSpace: 'pre-wrap',
												wordBreak: 'break-word'
											}}>
												{JSON.stringify(m.raw, null, 2)}
											</pre>
										)}
									</div>
								)}
								{m.timestamp && (
									<div style={{
										fontSize: '10px',
										color: '#6b7280',
										marginTop: '4px',
										marginLeft: '32px'
									}}>
										{formatTimestamp(m.timestamp)}
									</div>
								)}
							</div>
						</div>
					</div>
				))}
				{busy && (
					<div style={{
						display: 'flex',
						alignItems: 'flex-start',
						gap: '8px'
					}}>
						<div style={{
							width: '24px',
							height: '24px',
							borderRadius: '12px',
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							backgroundColor: '#3b82f6',
							flexShrink: 0
						}}>
							<div style={{
								width: '8px',
								height: '8px',
								borderRadius: '50%',
								backgroundColor: 'white',
								animation: 'pulse 1.5s ease-in-out infinite'
							}} />
						</div>
						<div style={{
							backgroundColor: '#1f2937',
							border: '1px solid #374151',
							borderRadius: '8px',
							padding: '10px 12px',
							color: '#9ca3af',
							fontSize: '13px'
						}}>
							Thinking...
						</div>
					</div>
				)}
				<div ref={messagesEndRef} />
			</div>
			
			<form 
				onSubmit={onSend} 
				style={{ 
					padding: '12px 16px',
					borderTop: '1px solid #333',
					flexShrink: 0,
					display: 'flex',
					gap: '8px'
				}}
			>
				<input
					style={{ 
						flex: 1,
						backgroundColor: '#0a0a0a',
						border: '1px solid #374151',
						borderRadius: '6px',
						padding: '8px 12px',
						color: '#e5e7eb',
						fontSize: '13px',
						outline: 'none'
					}}
					placeholder="Ask: tune to 104.1, scan FM, weather station..."
					value={input}
					onChange={e => setInput(e.target.value)}
					disabled={busy}
				/>
				<button 
					disabled={busy || !input.trim()} 
					type="submit"
					style={{
						backgroundColor: busy || !input.trim() ? '#374151' : '#3b82f6',
						border: 'none',
						borderRadius: '6px',
						padding: '8px 16px',
						color: 'white',
						fontSize: '13px',
						fontWeight: 500,
						cursor: busy || !input.trim() ? 'not-allowed' : 'pointer',
						opacity: busy || !input.trim() ? 0.5 : 1
					}}
				>
					{busy ? 'Sending...' : 'Send'}
				</button>
			</form>
			
			<style>{`
				@keyframes pulse {
					0%, 100% { opacity: 1; }
					50% { opacity: 0.5; }
				}
			`}</style>
		</div>
	)
}


