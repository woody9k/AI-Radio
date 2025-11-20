/**
 * WebSocket connection manager with exponential backoff reconnection
 */

import { io } from 'socket.io-client'

export class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url
    this.options = {
      reconnect: true,
      maxReconnectAttempts: Infinity,
      initialReconnectDelay: 1000,
      maxReconnectDelay: 30000,
      reconnectBackoff: 2.0,
      ...options
    }
    this.socket = null
    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.isManualClose = false
    this.listeners = new Map()
    this.connect()
  }

  connect() {
    if (this.socket?.connected) {
      return
    }

    try {
      this.socket = io(this.url, {
        reconnection: false, // We handle reconnection manually
        transports: ['websocket', 'polling']
      })

      this.socket.on('connect', () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.emit('connect')
      })

      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason)
        this.emit('disconnect', reason)
        
        if (!this.isManualClose && this.options.reconnect) {
          this.scheduleReconnect()
        }
      })

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error)
        this.emit('error', error)
        
        if (this.options.reconnect) {
          this.scheduleReconnect()
        }
      })

      // Forward all other events
      this.socket.onAny((event, ...args) => {
        this.emit(event, ...args)
      })
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      if (this.options.reconnect) {
        this.scheduleReconnect()
      }
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      this.emit('max_reconnect_attempts')
      return
    }

    const delay = Math.min(
      this.options.initialReconnectDelay * Math.pow(this.options.reconnectBackoff, this.reconnectAttempts),
      this.options.maxReconnectDelay
    )

    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts + 1} in ${delay}ms`)
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)

    // Also register with socket if it exists
    if (this.socket) {
      this.socket.on(event, callback)
    }
  }

  off(event, callback) {
    const listeners = this.listeners.get(event)
    if (listeners) {
      const index = listeners.indexOf(callback)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }

    if (this.socket) {
      this.socket.off(event, callback)
    }
  }

  emit(event, ...args) {
    const listeners = this.listeners.get(event)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(...args)
        } catch (error) {
          console.error(`Error in WebSocket listener for ${event}:`, error)
        }
      })
    }
  }

  disconnect() {
    this.isManualClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  getSocket() {
    return this.socket
  }

  isConnected() {
    return this.socket?.connected ?? false
  }
}

