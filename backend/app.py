"""
AI-Radio Flask Backend

Main Flask application with REST API and WebSocket server for real-time
spectrum data streaming and SDR control.
"""

import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import numpy as np

from sdr_interface import sdr_manager, SDRDevice
from signal_processor import SignalProcessor, WaterfallProcessor
from presets import preset_manager, Preset
from ml.data_handler import data_collector
from ml.signal_classifier import signal_classifier
from audio_demodulator import AudioDemodulator
from dataclasses import asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ai-radio-secret-key')

# Initialize extensions
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Global instances
signal_processor = SignalProcessor()
waterfall_processor = WaterfallProcessor()
audio_demodulator = AudioDemodulator()
current_device: Optional[SDRDevice] = None
streaming_active = False
streaming_thread: Optional[threading.Thread] = None
audio_streaming_active = False
audio_streaming_thread: Optional[threading.Thread] = None
audio_mode = 'FM'  # Current demodulation mode


@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get list of available RTL-SDR devices."""
    try:
        devices = sdr_manager.scan_devices()
        device_info = sdr_manager.get_all_device_info()
        
        return jsonify({
            'success': True,
            'devices': devices,
            'device_info': device_info
        })
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<int:device_index>/connect', methods=['POST'])
def connect_device(device_index):
    """Connect to a specific RTL-SDR device."""
    global current_device
    
    try:
        # Disconnect current device if any
        if current_device:
            current_device.disconnect()
            
        # Connect to new device
        success = sdr_manager.connect_device(device_index)
        if success:
            current_device = sdr_manager.get_device(device_index)
            
            # Set default parameters
            current_device.set_frequency(100e6)  # 100 MHz
            current_device.set_gain('auto')
            current_device.set_sample_rate(2.048e6)
            
            return jsonify({
                'success': True,
                'device_info': current_device.get_device_info()
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to connect to device'}), 500
            
    except Exception as e:
        logger.error(f"Error connecting to device {device_index}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/devices/<int:device_index>/disconnect', methods=['POST'])
def disconnect_device(device_index):
    """Disconnect from a specific RTL-SDR device."""
    global current_device, streaming_active
    
    try:
        streaming_active = False
        if current_device:
            current_device.disconnect()
            current_device = None
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error disconnecting device {device_index}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update SDR settings."""
    global current_device
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    if request.method == 'GET':
        try:
            device_info = current_device.get_device_info()
            return jsonify({
                'success': True,
                'settings': {
                    'frequency': device_info.get('frequency', 0),
                    'sample_rate': device_info.get('sample_rate', 0),
                    'gain': device_info.get('gain', 'auto'),
                    'bandwidth': device_info.get('bandwidth')
                }
            })
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            success = True
            errors = []
            
            # Update frequency
            if 'frequency' in data:
                if not current_device.set_frequency(float(data['frequency'])):
                    success = False
                    errors.append('Failed to set frequency')
            
            # Update sample rate
            if 'sample_rate' in data:
                if not current_device.set_sample_rate(float(data['sample_rate'])):
                    success = False
                    errors.append('Failed to set sample rate')
                else:
                    # Update signal processor sample rate
                    signal_processor.set_sample_rate(float(data['sample_rate']))
            
            # Update gain
            if 'gain' in data:
                if not current_device.set_gain(data['gain']):
                    success = False
                    errors.append('Failed to set gain')
            
            # Update bandwidth
            if 'bandwidth' in data and data['bandwidth']:
                if not current_device.set_bandwidth(float(data['bandwidth'])):
                    success = False
                    errors.append('Failed to set bandwidth')
            
            if success:
                return jsonify({
                    'success': True,
                    'settings': current_device.get_device_info()
                })
            else:
                return jsonify({
                    'success': False,
                    'errors': errors
                }), 400
                
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stream/start', methods=['POST'])
def start_streaming():
    """Start real-time spectrum streaming."""
    global current_device, streaming_active, streaming_thread
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    if streaming_active:
        return jsonify({'success': False, 'error': 'Already streaming'}), 400
    
    try:
        # Start streaming in a separate thread
        streaming_active = True
        streaming_thread = threading.Thread(target=streaming_worker, daemon=True)
        streaming_thread.start()
        
        # Start data collection
        data_collector.start_collection()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        streaming_active = False
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stream/stop', methods=['POST'])
def stop_streaming():
    """Stop real-time spectrum streaming."""
    global streaming_active
    
    try:
        streaming_active = False
        
        # Stop data collection
        data_collector.stop_collection()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/spectrum', methods=['GET'])
def get_spectrum():
    """Get a single spectrum reading."""
    global current_device
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    try:
        # Read samples
        samples = current_device.read_samples(signal_processor.fft_size)
        if samples is None:
            return jsonify({'success': False, 'error': 'Failed to read samples'}), 500
        
        # Process spectrum
        freqs, spectrum = signal_processor.compute_fft(samples)
        
        # Detect signals
        signals = signal_processor.detect_signals(spectrum, current_device.frequency)
        
        # Extract features for classification
        features = signal_processor.extract_features(samples)
        
        # Classify each detected signal
        for signal in signals:
            try:
                classification = signal_classifier.classify_signal(
                    frequency=signal['frequency'],
                    features=features,
                    spectrum=spectrum,
                    signal_info=signal
                )
                signal['category'] = classification.category
                signal['confidence'] = classification.confidence
                signal['modulation'] = classification.modulation
                signal['description'] = classification.description
                signal['technical_details'] = classification.technical_details
            except Exception as e:
                logger.error(f"Error classifying signal in spectrum endpoint: {e}")
                signal['category'] = 'unknown'
                signal['confidence'] = 0.0
                signal['modulation'] = 'Unknown'
                signal['description'] = 'Unknown Signal'
                signal['technical_details'] = {}
        
        return jsonify({
            'success': True,
            'frequencies': freqs.tolist(),
            'spectrum': spectrum.tolist(),
            'signals': signals,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting spectrum: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Get all available presets."""
    try:
        category = request.args.get('category')
        search = request.args.get('search')
        
        if search:
            presets = preset_manager.search_presets(search)
        elif category:
            presets = preset_manager.get_presets_by_category(category)
        else:
            presets = preset_manager.get_presets_by_category()
        
        return jsonify({
            'success': True,
            'presets': [preset.to_dict() for preset in presets],
            'categories': preset_manager.get_categories()
        })
    except Exception as e:
        logger.error(f"Error getting presets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets/<preset_name>/apply', methods=['POST'])
def apply_preset(preset_name):
    """Apply a preset configuration to the current device."""
    global current_device
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    try:
        preset = preset_manager.get_preset(preset_name)
        if not preset:
            return jsonify({'success': False, 'error': 'Preset not found'}), 404
        
        # Apply preset settings
        success = True
        errors = []
        
        if not current_device.set_frequency(preset.frequency):
            success = False
            errors.append('Failed to set frequency')
        
        if not current_device.set_sample_rate(preset.sample_rate):
            success = False
            errors.append('Failed to set sample rate')
        else:
            signal_processor.set_sample_rate(preset.sample_rate)
        
        if not current_device.set_gain(preset.gain):
            success = False
            errors.append('Failed to set gain')
        
        if preset.bandwidth and not current_device.set_bandwidth(preset.bandwidth):
            success = False
            errors.append('Failed to set bandwidth')
        
        if success:
            # Increment usage count
            preset_manager.increment_usage(preset_name)
            
            return jsonify({
                'success': True,
                'preset': preset.to_dict(),
                'device_info': current_device.get_device_info()
            })
        else:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
            
    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets', methods=['POST'])
def create_preset():
    """Create a new custom preset."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'frequency']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create preset
        preset = Preset(
            name=data['name'],
            description=data['description'],
            frequency=data['frequency'],
            sample_rate=data.get('sample_rate', 2048000),
            gain=data.get('gain', 'auto'),
            bandwidth=data.get('bandwidth'),
            category=data.get('category', 'Custom'),
            tips=data.get('tips', [])
        )
        
        # Add to manager
        if preset_manager.add_custom_preset(preset):
            return jsonify({
                'success': True,
                'preset': preset.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create preset'}), 500
            
    except Exception as e:
        logger.error(f"Error creating preset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/presets/<preset_name>', methods=['DELETE'])
def delete_preset(preset_name):
    """Delete a custom preset."""
    try:
        if preset_manager.delete_custom_preset(preset_name):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Preset not found or not deletable'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting preset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/statistics', methods=['GET'])
def get_data_statistics():
    """Get data collection statistics."""
    try:
        stats = data_collector.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting data statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/datasets', methods=['GET'])
def get_datasets():
    """Get all available datasets."""
    try:
        datasets = data_collector.get_datasets()
        return jsonify({
            'success': True,
            'datasets': [asdict(dataset) for dataset in datasets]
        })
    except Exception as e:
        logger.error(f"Error getting datasets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/data/datasets', methods=['POST'])
def create_dataset():
    """Create a new training dataset."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data or 'description' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields: name, description'}), 400
        
        dataset = data_collector.create_dataset(
            name=data['name'],
            description=data['description'],
            categories=data.get('categories')
        )
        
        return jsonify({
            'success': True,
            'dataset': asdict(dataset)
        })
        
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classifications', methods=['GET'])
def get_classifications():
    """Get recent signal classifications."""
    try:
        stats = signal_classifier.get_classification_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting classifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classifications/stats', methods=['GET'])
def get_classification_stats():
    """Get detailed classification statistics."""
    try:
        stats = signal_classifier.get_classification_stats()
        categories = signal_classifier.get_available_categories()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'available_categories': categories
        })
    except Exception as e:
        logger.error(f"Error getting classification stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audio/start', methods=['POST'])
def start_audio():
    """Start audio demodulation and streaming."""
    global audio_streaming_active, audio_streaming_thread, audio_mode, current_device
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    if audio_streaming_active:
        return jsonify({'success': False, 'error': 'Audio already streaming'}), 400
    
    try:
        data = request.get_json() or {}
        audio_mode = data.get('mode', 'FM').upper()
        
        # Optional: tune to specific frequency if provided
        if 'frequency' in data:
            current_device.set_frequency(int(data['frequency']))
        
        # Update audio demodulator sample rate
        audio_demodulator.update_sample_rate(current_device.sample_rate)
        
        # Start audio streaming thread
        audio_streaming_active = True
        audio_streaming_thread = threading.Thread(target=audio_worker, daemon=True)
        audio_streaming_thread.start()
        
        logger.info(f"Started audio streaming in {audio_mode} mode")
        
        return jsonify({
            'success': True,
            'mode': audio_mode,
            'frequency': current_device.frequency,
            'sample_rate': current_device.sample_rate
        })
    except Exception as e:
        logger.error(f"Error starting audio: {e}")
        audio_streaming_active = False
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audio/stop', methods=['POST'])
def stop_audio():
    """Stop audio demodulation and streaming."""
    global audio_streaming_active, audio_streaming_thread
    
    if not audio_streaming_active:
        return jsonify({'success': False, 'error': 'Audio not streaming'}), 400
    
    try:
        audio_streaming_active = False
        
        # Wait for thread to finish
        if audio_streaming_thread and audio_streaming_thread.is_alive():
            audio_streaming_thread.join(timeout=2.0)
        
        logger.info("Stopped audio streaming")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tune_signal', methods=['POST'])
def tune_signal():
    """Smart tuning: tune to a signal and start audio with appropriate settings."""
    global current_device, audio_mode
    
    if not current_device or not current_device.is_connected:
        return jsonify({'success': False, 'error': 'No device connected'}), 400
    
    try:
        data = request.get_json()
        
        # Extract signal parameters
        frequency = data.get('frequency')
        bandwidth = data.get('bandwidth')
        modulation = data.get('modulation', 'FM')
        
        if not frequency:
            return jsonify({'success': False, 'error': 'Frequency required'}), 400
        
        # Tune to frequency
        current_device.set_frequency(int(frequency))
        
        # Set bandwidth if provided and device supports it
        if bandwidth:
            try:
                current_device.set_bandwidth(int(bandwidth))
            except Exception as e:
                logger.warning(f"Could not set bandwidth: {e}")
        
        # Determine audio mode from modulation
        if 'AM' in modulation.upper():
            audio_mode = 'AM'
        elif 'FM' in modulation.upper():
            audio_mode = 'FM'
        else:
            audio_mode = 'FM'  # Default
        
        # Start audio streaming
        response = start_audio()
        
        logger.info(f"Tuned to signal at {frequency/1e6:.3f} MHz ({modulation})")
        
        return response
        
    except Exception as e:
        logger.error(f"Error tuning to signal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classifications/label', methods=['POST'])
def label_signal():
    """Manually label a signal for training."""
    try:
        data = request.get_json()
        frequency = data.get('frequency')
        category = data.get('category')
        modulation = data.get('modulation')
        
        if not frequency or not category:
            return jsonify({'success': False, 'error': 'Frequency and category required'}), 400
        
        # Store manual label for future training
        # This would integrate with the data collection system
        logger.info(f"Manual label: {frequency} Hz -> {category} ({modulation})")
        
        return jsonify({
            'success': True,
            'message': f'Labeled {frequency} Hz as {category}'
        })
        
    except Exception as e:
        logger.error(f"Error labeling signal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to AI-Radio server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('join_room')
def handle_join_room(data):
    """Handle client joining a room."""
    room = data.get('room', 'default')
    join_room(room)
    emit('status', {'message': f'Joined room: {room}'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle client leaving a room."""
    room = data.get('room', 'default')
    leave_room(room)
    emit('status', {'message': f'Left room: {room}'})


def audio_worker():
    """Worker thread for audio demodulation and streaming."""
    global current_device, audio_streaming_active, audio_mode, audio_demodulator
    
    logger.info(f"Starting audio worker in {audio_mode} mode")
    
    # Buffer size for reading samples (adjust for smooth audio)
    buffer_size = 65536  # Larger buffer for audio processing
    
    while audio_streaming_active and current_device and current_device.is_connected:
        try:
            # Read IQ samples
            samples = current_device.read_samples(buffer_size)
            if samples is None:
                time.sleep(0.01)
                continue
            
            # Demodulate to audio
            audio = audio_demodulator.demodulate(samples, mode=audio_mode)
            
            # Convert to format suitable for web audio (float32 array to list)
            audio_data = audio.tolist()
            
            # Emit audio data via WebSocket
            socketio.emit('audio_samples', {
                'samples': audio_data,
                'sample_rate': audio_demodulator.audio_rate,
                'mode': audio_mode
            })
            
            # Small sleep to prevent overwhelming the socket
            time.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error in audio worker: {e}")
            time.sleep(0.1)
    
    logger.info("Audio worker stopped")


def streaming_worker():
    """Worker thread for real-time spectrum streaming."""
    global current_device, streaming_active, signal_processor, waterfall_processor
    
    logger.info("Starting streaming worker")
    
    while streaming_active and current_device and current_device.is_connected:
        try:
            # Read samples
            samples = current_device.read_samples(signal_processor.fft_size)
            if samples is None:
                time.sleep(0.1)
                continue
            
            # Process spectrum
            freqs, spectrum = signal_processor.compute_fft(samples)
            
            # Add to waterfall
            waterfall_processor.add_spectrum(spectrum)
            
            # Detect signals
            signals = signal_processor.detect_signals(spectrum, current_device.frequency)
            
            # Extract features for AI processing
            features = signal_processor.extract_features(samples)
            
            # Classify each detected signal
            for signal in signals:
                try:
                    classification = signal_classifier.classify_signal(
                        frequency=signal['frequency'],
                        features=features,
                        spectrum=spectrum,
                        signal_info=signal
                    )
                    signal['category'] = classification.category
                    signal['confidence'] = classification.confidence
                    signal['modulation'] = classification.modulation
                    signal['description'] = classification.description
                    signal['technical_details'] = classification.technical_details
                    logger.info(f"Classified signal at {signal['frequency']/1e6:.3f} MHz as {classification.category} (confidence: {classification.confidence:.2f})")
                except Exception as e:
                    logger.error(f"Error classifying signal: {e}")
                    signal['category'] = 'unknown'
                    signal['confidence'] = 0.0
                    signal['modulation'] = 'Unknown'
                    signal['description'] = 'Unknown Signal'
                    signal['technical_details'] = {}
            
            # Collect data for ML training
            data_collector.add_sample(
                samples=samples,
                spectrum=spectrum,
                frequency=current_device.frequency,
                sample_rate=current_device.sample_rate,
                gain=current_device.gain,
                signals_detected=signals
            )
            
            # Debug: Check if signals have classification
            classified_count = sum(1 for s in signals if 'category' in s)
            logger.info(f"Emitting {len(signals)} signals, {classified_count} with classification")
            
            # Emit spectrum data
            socketio.emit('spectrum_data', {
                'frequencies': freqs.tolist(),
                'spectrum': spectrum.tolist(),
                'signals': signals,
                'features': features,
                'timestamp': datetime.now().isoformat()
            })
            
            # Emit waterfall data (less frequently)
            if int(time.time() * 10) % 5 == 0:  # Every 0.5 seconds
                waterfall_data = waterfall_processor.get_waterfall()
                socketio.emit('waterfall_data', {
                    'data': waterfall_data.tolist(),
                    'timestamp': datetime.now().isoformat()
                })
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in streaming worker: {e}")
            time.sleep(0.1)
    
    logger.info("Streaming worker stopped")


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
