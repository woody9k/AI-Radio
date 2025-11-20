"""
AI-Radio Flask Backend

Main Flask application with REST API and WebSocket server for real-time
spectrum data streaming and SDR control.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime

import numpy as np
from audio_demodulator import AudioDemodulator
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from ml.data_handler import data_collector
from ml.signal_classifier import signal_classifier
from presets import Preset, preset_manager
from sdr_interface import SDRDevice, sdr_manager
from signal_processor import SignalProcessor, WaterfallProcessor

# AI modules are imported lazily inside the handler to avoid hard dependency at startup
from backend.database.db import get_db_session, init_database
from backend.database.models import Classification, Recording, Signal
from backend.settings import get_settings, update_settings
from recording import recording_manager

# Initialize database
init_database()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ai-radio-secret-key")

# Initialize extensions
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Global instances
signal_processor = SignalProcessor()
waterfall_processor = WaterfallProcessor()
audio_demodulator = AudioDemodulator()
current_device: SDRDevice | None = None
streaming_active = False
streaming_thread: threading.Thread | None = None
audio_streaming_active = False
audio_streaming_thread: threading.Thread | None = None
audio_mode = "FM"  # Current demodulation mode


@app.route("/")
def index():
    """Serve the main application page."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    global current_device, streaming_active
    return jsonify(
        {
            "success": True,
            "device_connected": (
                current_device is not None and current_device.is_connected
                if current_device
                else False
            ),
            "streaming": streaming_active,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/settings/ai", methods=["GET", "POST"])
def ai_settings():
    """Get or update AI settings (OpenAI key, model, provider)."""
    if request.method == "GET":
        settings = get_settings().copy()
        # Mask the API key
        if settings.get("openai_api_key"):
            settings["openai_api_key"] = "****"
        return jsonify({"success": True, "settings": settings})

    data = request.get_json() or {}
    saved = update_settings(
        {
            "openai_api_key": data.get("openai_api_key"),
            "openai_model": data.get("openai_model"),
            "provider": data.get("provider"),
            "auto_execute": data.get("auto_execute"),
            "region": data.get("region"),
            "theme": data.get("theme"),
        }
    )
    # Mask in response
    if saved.get("openai_api_key"):
        saved["openai_api_key"] = "****"
    return jsonify({"success": True, "settings": saved})


def _read_spectrum_at(center_freq_hz):
    """Helper for scanning utilities: tune and return a single FFT frame (freqs, spectrum_db)."""
    global current_device
    try:
        if not current_device or not current_device.is_connected:
            return None, None
        current_device.set_frequency(float(center_freq_hz))
        samples = current_device.read_samples(signal_processor.fft_size)
        if samples is None:
            return None, None
        freqs, spectrum = signal_processor.compute_fft(samples)
        spectrum_db = 10 * np.log10(np.maximum(np.abs(spectrum), 1e-12))
        return freqs, spectrum_db
    except Exception:
        return None, None


@app.route("/api/ai/command", methods=["POST"])
def ai_command():
    """Parse and optionally execute a natural-language command via OpenAI."""
    global current_device
    data = request.get_json() or {}
    text = data.get("text", "")
    dry_run = bool(data.get("dry_run", False))

    try:
        # Lazy import to keep startup resilient
        from backend.ai.intent_router import execute_intent
        from backend.ai.intent_schema import IntentParseResult
        from backend.ai.openai_client import OpenAIClient
        from backend.ai.prompt_templates import SYSTEM_PROMPT

        client = OpenAIClient()
        parsed = client.parse_intent(text, SYSTEM_PROMPT)
        # Validate structure if pydantic available
        try:
            _ = IntentParseResult(
                **{
                    "intent": parsed.get("intent"),
                    "params": parsed.get("params", {}),
                    "meta": parsed.get("meta"),
                    "explanation": parsed.get("explanation"),
                }
            )
        except Exception:
            pass

        result = {"success": True, "intent": parsed}

        if not dry_run:
            exec_ctx = {
                "current_device": current_device,
                "signal_processor": signal_processor,
                "read_spectrum_fn": _read_spectrum_at,
                "preset_manager": preset_manager,
            }
            exec_res = execute_intent(parsed, exec_ctx)
            result["executed"] = True
            result["result"] = exec_res
        else:
            result["executed"] = False

        return jsonify(result)
    except Exception as e:
        logger.error(f"AI command error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/devices", methods=["GET"])
def get_devices():
    """Get list of available RTL-SDR devices."""
    try:
        devices = sdr_manager.scan_devices()
        device_info = sdr_manager.get_all_device_info()

        return jsonify({"success": True, "devices": devices, "device_info": device_info})
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/devices/<int:device_index>/connect", methods=["POST"])
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
            current_device.set_frequency(104.1e6)  # 104.1 MHz default
            current_device.set_gain("auto")
            current_device.set_sample_rate(2.048e6)

            return jsonify({"success": True, "device_info": current_device.get_device_info()})
        else:
            return jsonify({"success": False, "error": "Failed to connect to device"}), 500

    except Exception as e:
        logger.error(f"Error connecting to device {device_index}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/devices/<int:device_index>/disconnect", methods=["POST"])
def disconnect_device(device_index):
    """Disconnect from a specific RTL-SDR device."""
    global current_device, streaming_active

    try:
        streaming_active = False
        if current_device:
            current_device.disconnect()
            current_device = None

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error disconnecting device {device_index}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _settings_get_payload(device: SDRDevice) -> dict:
    device_info = device.get_device_info()
    return {
        "success": True,
        "settings": {
            "frequency": device_info.get("frequency", 0),
            "sample_rate": device_info.get("sample_rate", 0),
            "gain": device_info.get("gain", "auto"),
            "bandwidth": device_info.get("bandwidth"),
            "mode": device_info.get("mode", "WFM"),
            "agc_enabled": device_info.get("agc_enabled", False),
            "bias_t": device_info.get("bias_t", False),
            "capabilities": device_info.get("capabilities", {}),
        },
    }


SettingOp = tuple[str, Callable[[], bool | None]]


def _op_frequency(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "frequency" not in data:
        return []
    freq = float(data["frequency"])
    return [("Failed to set frequency", lambda: device.set_frequency(freq))]


def _op_sample_rate(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "sample_rate" not in data:
        return []
    sr = float(data["sample_rate"])

    def set_sr() -> bool:
        ok = device.set_sample_rate(sr)
        if ok:
            signal_processor.set_sample_rate(sr)
        return bool(ok)

    return [("Failed to set sample rate", set_sr)]


def _op_gain(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "gain" not in data:
        return []
    g = data["gain"]
    return [("Failed to set gain", lambda: device.set_gain(g))]


def _op_bandwidth(device: SDRDevice, data: dict) -> list[SettingOp]:
    if not data.get("bandwidth"):
        return []
    bw = float(data["bandwidth"])
    return [("Failed to set bandwidth", lambda: device.set_bandwidth(bw))]


def _op_mode(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "mode" not in data:
        return []
    m = data["mode"]

    def set_mode() -> bool:
        ok = device.set_mode(m)
        if ok:
            audio_demodulator.set_mode(m)
        return bool(ok)

    return [("Failed to set mode", set_mode)]


def _op_agc(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "agc_enabled" not in data:
        return []
    agc = bool(data["agc_enabled"])
    return [("Failed to set AGC", lambda: device.set_agc(agc))]


def _op_bias_t(device: SDRDevice, data: dict) -> list[SettingOp]:
    if "bias_t" not in data:
        return []
    bt = bool(data["bias_t"])

    def set_bias() -> bool:
        ok = device.set_bias_t(bt)
        # If unsupported, treat as no-op without error
        return bool(ok or not device.device_capabilities.get("bias_t", False))

    return [("Failed to set bias-T", set_bias)]


def _op_squelch(device: SDRDevice, data: dict) -> list[SettingOp]:
    if ("squelch_threshold" not in data) and ("squelch_enabled" not in data):
        return []
    th = float(data.get("squelch_threshold", audio_demodulator.squelch_threshold))
    en = bool(data.get("squelch_enabled", audio_demodulator.squelch_enabled))

    def set_squelch() -> bool:
        audio_demodulator.set_squelch(th, en)
        return True

    return [("Failed to set squelch", set_squelch)]


def _build_setting_ops(device: SDRDevice, data: dict) -> list[SettingOp]:
    ops: list[SettingOp] = []
    ops += _op_frequency(device, data)
    ops += _op_sample_rate(device, data)
    ops += _op_gain(device, data)
    ops += _op_bandwidth(device, data)
    ops += _op_mode(device, data)
    ops += _op_agc(device, data)
    ops += _op_bias_t(device, data)
    ops += _op_squelch(device, data)
    return ops


def _apply_settings_post(device: SDRDevice, data: dict) -> tuple[bool, list[str]]:
    def try_call(label: str, func: Callable[[], bool | None]) -> tuple[bool, str | None]:
        try:
            ok = func()
            return (True if ok is None else bool(ok)), None
        except Exception as exc:  # narrow handlers live inside device methods
            return False, f"{label}: {exc}"

    operations = _build_setting_ops(device, data)

    success = True
    errors: list[str] = []
    for label, fn in operations:
        ok, err = try_call(label, fn)
        if not ok:
            success = False
            errors.append(label if err is None else err)

    return success, errors


@app.route("/api/settings", methods=["GET", "POST"])
def handle_settings():
    """Get or update SDR settings."""
    global current_device

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    if request.method == "GET":
        try:
            return jsonify(_settings_get_payload(current_device))
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    try:
        data = request.get_json() or {}
        success, errors = _apply_settings_post(current_device, data)
        if success:
            return jsonify({"success": True, "settings": current_device.get_device_info()})
        return jsonify({"success": False, "errors": errors}), 400
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stream/start", methods=["POST"])
def start_streaming():
    """Start real-time spectrum streaming."""
    global current_device, streaming_active, streaming_thread

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    if streaming_active:
        return jsonify({"success": False, "error": "Already streaming"}), 400

    try:
        # Start streaming in a separate thread
        streaming_active = True
        streaming_thread = threading.Thread(target=streaming_worker, daemon=True)
        streaming_thread.start()

        # Start data collection
        data_collector.start_collection()

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        streaming_active = False
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stream/stop", methods=["POST"])
def stop_streaming():
    """Stop real-time spectrum streaming."""
    global streaming_active

    try:
        streaming_active = False

        # Stop data collection
        data_collector.stop_collection()

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/spectrum", methods=["GET"])
def get_spectrum():
    """Get a single spectrum reading."""
    global current_device

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    try:
        # Read samples
        samples = current_device.read_samples(signal_processor.fft_size)
        if samples is None:
            return jsonify({"success": False, "error": "Failed to read samples"}), 500

        # Process spectrum
        freqs, spectrum = signal_processor.compute_fft(samples)
        center_freq = float(current_device.frequency)
        sample_rate = float(current_device.sample_rate)
        resolution_hz = float(signal_processor.get_frequency_resolution())
        abs_freqs = (freqs + center_freq).tolist()

        # Detect signals
        signals = signal_processor.detect_signals(spectrum, current_device.frequency)

        # Extract features for classification
        features = signal_processor.extract_features(samples)

        # Classify each detected signal
        for signal in signals:
            try:
                classification = signal_classifier.classify_signal(
                    frequency=signal["frequency"],
                    features=features,
                    spectrum=spectrum,
                    signal_info=signal,
                )
                signal["category"] = classification.category
                signal["confidence"] = classification.confidence
                signal["modulation"] = classification.modulation
                signal["description"] = classification.description
                signal["technical_details"] = classification.technical_details
            except Exception as e:
                logger.error(f"Error classifying signal in spectrum endpoint: {e}")
                signal["category"] = "unknown"
                signal["confidence"] = 0.0
                signal["modulation"] = "Unknown"
                signal["description"] = "Unknown Signal"
                signal["technical_details"] = {}

        return jsonify(
            {
                "success": True,
                "frequencies": freqs.tolist(),
                "absolute_frequencies": abs_freqs,
                "center_frequency": center_freq,
                "sample_rate": sample_rate,
                "resolution_hz": resolution_hz,
                "spectrum": spectrum.tolist(),
                "signals": signals,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error getting spectrum: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/spectrum/zoom", methods=["GET"])
def get_spectrum_zoom():
    """Return a high-resolution spectrum slice around the current center using decimation.

    Query params:
      - center: center frequency in Hz (optional; defaults to device center)
      - span: desired span in Hz (optional; defaults to 100e3)
      - fft: fft size hint (optional; defaults to 8192)
    Notes:
      - For simplicity, the decimation assumes the requested center matches the device center.
        If they differ by more than 10% of the current span, we clamp to device center.
    """
    global current_device
    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    try:
        device_center = float(current_device.frequency)
        sample_rate = float(current_device.sample_rate)
        center = float(request.args.get("center", device_center))
        span = float(request.args.get("span", 100e3))
        fft_hint = int(request.args.get("fft", 8192))

        # Clamp unreasonable inputs
        span = max(5e3, min(sample_rate, span))
        fft_size = max(2048, min(16384, fft_hint))

        # Keep center aligned with device center for v1
        if abs(center - device_center) > (0.1 * sample_rate):
            center = device_center

        # Determine decimation so that post-decimation span ~= requested span
        # Post-decimation Nyquist is sr_decim/2, so displayed span ~= sr_decim
        # We want sr_decim ~= span -> decim = sample_rate / span
        decimation = int(np.ceil(sample_rate / span))
        decimation = max(1, min(32, decimation))
        sr_decim = sample_rate / decimation

        # Read enough samples for desired FFT size at decimated rate
        # Heuristic: read 2x FFT worth of samples then take the last FFT window
        read_count = fft_size * decimation * 2
        samples = current_device.read_samples(read_count)
        if samples is None or len(samples) == 0:
            return jsonify({"success": False, "error": "Failed to read samples"}), 500

        # Digital down-conversion would allow arbitrary centers; for now assume centered
        # Apply simple low-pass decimation using signal_processor helper
        try:
            decimated = signal_processor.decimate(samples, decimation)
        except Exception:
            # Fallback: naive downsample
            decimated = samples[::decimation]

        # Use a larger FFT for higher resolution
        original_fft = signal_processor.fft_size
        original_sr = signal_processor.sample_rate
        try:
            signal_processor.set_sample_rate(sr_decim)
            signal_processor.set_fft_size(fft_size)
            freqs_rel, spectrum = signal_processor.compute_fft(decimated[-fft_size:])
        finally:
            signal_processor.set_sample_rate(original_sr)
            signal_processor.set_fft_size(original_fft)

        freqs_abs = (freqs_rel + center).tolist()
        resolution_hz = sr_decim / fft_size

        return jsonify(
            {
                "success": True,
                "center_frequency": center,
                "sample_rate": sr_decim,
                "resolution_hz": resolution_hz,
                "frequencies": freqs_rel.tolist(),
                "absolute_frequencies": freqs_abs,
                "spectrum": spectrum.tolist(),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error getting zoom spectrum: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Get all available presets."""
    try:
        category = request.args.get("category")
        search = request.args.get("search")

        if search:
            presets = preset_manager.search_presets(search)
        elif category:
            presets = preset_manager.get_presets_by_category(category)
        else:
            presets = preset_manager.get_presets_by_category()

        return jsonify(
            {
                "success": True,
                "presets": [preset.to_dict() for preset in presets],
                "categories": preset_manager.get_categories(),
            }
        )
    except Exception as e:
        logger.error(f"Error getting presets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/presets/<preset_name>/apply", methods=["POST"])
def apply_preset(preset_name):
    """Apply a preset configuration to the current device."""
    global current_device

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    try:
        preset = preset_manager.get_preset(preset_name)
        if not preset:
            return jsonify({"success": False, "error": "Preset not found"}), 404

        # Apply preset settings
        success = True
        errors = []

        if not current_device.set_frequency(preset.frequency):
            success = False
            errors.append("Failed to set frequency")

        if not current_device.set_sample_rate(preset.sample_rate):
            success = False
            errors.append("Failed to set sample rate")
        else:
            signal_processor.set_sample_rate(preset.sample_rate)

        if not current_device.set_gain(preset.gain):
            success = False
            errors.append("Failed to set gain")

        if preset.bandwidth and not current_device.set_bandwidth(preset.bandwidth):
            success = False
            errors.append("Failed to set bandwidth")

        if success:
            # Track preset usage
            preset_manager.track_preset_usage(preset_name)

            return jsonify(
                {
                    "success": True,
                    "preset": preset.to_dict(),
                    "device_info": current_device.get_device_info(),
                }
            )
        else:
            return jsonify({"success": False, "errors": errors}), 400

    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/presets", methods=["POST"])
def create_preset():
    """Create a new custom preset."""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["name", "description", "frequency"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        # Create preset
        preset = Preset(
            name=data["name"],
            description=data["description"],
            frequency=data["frequency"],
            sample_rate=data.get("sample_rate", 2048000),
            gain=data.get("gain", "auto"),
            bandwidth=data.get("bandwidth"),
            category=data.get("category", "Custom"),
            tips=data.get("tips", []),
        )

        # Add to manager
        if preset_manager.add_custom_preset(preset):
            return jsonify({"success": True, "preset": preset.to_dict()})
        else:
            return jsonify({"success": False, "error": "Failed to create preset"}), 500

    except Exception as e:
        logger.error(f"Error creating preset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/presets/<preset_name>", methods=["DELETE"])
def delete_preset(preset_name):
    """Delete a custom preset."""
    try:
        if preset_manager.delete_custom_preset(preset_name):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Preset not found or not deletable"}), 404

    except Exception as e:
        logger.error(f"Error deleting preset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/data/statistics", methods=["GET"])
def get_data_statistics():
    """Get data collection statistics."""
    try:
        stats = data_collector.get_statistics()
        return jsonify({"success": True, "statistics": stats})
    except Exception as e:
        logger.error(f"Error getting data statistics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/data/datasets", methods=["GET"])
def get_datasets():
    """Get all available datasets."""
    try:
        datasets = data_collector.get_datasets()
        return jsonify({"success": True, "datasets": [asdict(dataset) for dataset in datasets]})
    except Exception as e:
        logger.error(f"Error getting datasets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/data/datasets", methods=["POST"])
def create_dataset():
    """Create a new training dataset."""
    try:
        data = request.get_json()

        # Validate required fields
        if "name" not in data or "description" not in data:
            return (
                jsonify({"success": False, "error": "Missing required fields: name, description"}),
                400,
            )

        dataset = data_collector.create_dataset(
            name=data["name"], description=data["description"], categories=data.get("categories")
        )

        return jsonify({"success": True, "dataset": asdict(dataset)})

    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/classifications", methods=["GET"])
def get_classifications():
    """Get recent signal classifications."""
    try:
        stats = signal_classifier.get_classification_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Error getting classifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/classifications/stats", methods=["GET"])
def get_classification_stats():
    """Get detailed classification statistics."""
    try:
        stats = signal_classifier.get_classification_stats()
        categories = signal_classifier.get_available_categories()

        return jsonify({"success": True, "stats": stats, "available_categories": categories})
    except Exception as e:
        logger.error(f"Error getting classification stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/audio/start", methods=["POST"])
def start_audio():
    """Start audio demodulation and streaming."""
    global audio_streaming_active, audio_streaming_thread, audio_mode, current_device

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    if audio_streaming_active:
        return jsonify({"success": False, "error": "Audio already streaming"}), 400

    try:
        data = request.get_json() or {}
        audio_mode = data.get("mode", "FM").upper()

        # Optional: tune to specific frequency if provided
        if "frequency" in data:
            current_device.set_frequency(int(data["frequency"]))

        # Update audio demodulator sample rate
        audio_demodulator.update_sample_rate(current_device.sample_rate)

        # Start audio streaming thread
        audio_streaming_active = True
        audio_streaming_thread = threading.Thread(target=audio_worker, daemon=True)
        audio_streaming_thread.start()

        logger.info(f"Started audio streaming in {audio_mode} mode")

        return jsonify(
            {
                "success": True,
                "mode": audio_mode,
                "frequency": current_device.frequency,
                "sample_rate": current_device.sample_rate,
            }
        )
    except Exception as e:
        logger.error(f"Error starting audio: {e}")
        audio_streaming_active = False
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/audio/stop", methods=["POST"])
def stop_audio():
    """Stop audio demodulation and streaming."""
    global audio_streaming_active, audio_streaming_thread

    if not audio_streaming_active:
        return jsonify({"success": False, "error": "Audio not streaming"}), 400

    try:
        audio_streaming_active = False

        # Wait for thread to finish
        if audio_streaming_thread and audio_streaming_thread.is_alive():
            audio_streaming_thread.join(timeout=2.0)

        logger.info("Stopped audio streaming")

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/start", methods=["POST"])
def start_recording():
    """Start recording IQ samples."""
    global current_device
    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    try:
        data = request.get_json() or {}
        description = data.get("description")
        mode = data.get("mode", "FM")

        result = recording_manager.start_recording(
            frequency=current_device.frequency,
            sample_rate=current_device.sample_rate,
            gain=str(current_device.gain),
            mode=mode,
            description=description,
        )

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/stop", methods=["POST"])
def stop_recording():
    """Stop recording and save metadata."""
    try:
        result = recording_manager.stop_recording()
        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/status", methods=["GET"])
def get_recording_status():
    """Get current recording status."""
    try:
        status = recording_manager.get_recording_status()
        return jsonify({"success": True, **status})
    except Exception as e:
        logger.error(f"Error getting recording status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/list", methods=["GET"])
def list_recordings():
    """List all recordings."""
    try:
        recordings = recording_manager.list_recordings()
        return jsonify({"success": True, "recordings": recordings})
    except Exception as e:
        logger.error(f"Error listing recordings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/<filename>", methods=["GET"])
def get_recording(filename):
    """Get metadata for a specific recording."""
    try:
        recording = recording_manager.get_recording(filename)
        if recording:
            return jsonify({"success": True, "recording": recording})
        else:
            return jsonify({"success": False, "error": "Recording not found"}), 404
    except Exception as e:
        logger.error(f"Error getting recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recording/<filename>/download", methods=["GET"])
def download_recording(filename):
    """Download a recording file."""
    try:
        filepath = recording_manager.get_recording_filepath(filename)
        if filepath and filepath.exists():
            return send_file(
                str(filepath),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=filename,
            )
        else:
            return jsonify({"success": False, "error": "Recording not found"}), 404
    except Exception as e:
        logger.error(f"Error downloading recording: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/signals", methods=["GET"])
def get_signals():
    """Get signals from database with filtering."""
    try:
        freq_min = request.args.get("freq_min", type=float)
        freq_max = request.args.get("freq_max", type=float)
        category = request.args.get("category")
        limit = request.args.get("limit", type=int, default=100)

        with get_db_session() as session:
            query = session.query(Signal)

            if freq_min:
                query = query.filter(Signal.frequency >= freq_min)
            if freq_max:
                query = query.filter(Signal.frequency <= freq_max)
            if category:
                query = query.filter(Signal.category == category)

            query = query.order_by(Signal.timestamp.desc()).limit(limit)
            signals = query.all()

            return jsonify({
                "success": True,
                "signals": [s.to_dict() for s in signals]
            })
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/signals/search", methods=["GET"])
def search_signals():
    """Search signals by description or category."""
    try:
        q = request.args.get("q", "")
        if not q:
            return jsonify({"success": False, "error": "Query parameter 'q' required"}), 400

        with get_db_session() as session:
            query = session.query(Signal).filter(
                (Signal.description.contains(q)) | (Signal.category.contains(q))
            ).order_by(Signal.timestamp.desc()).limit(50)

            signals = query.all()
            return jsonify({
                "success": True,
                "signals": [s.to_dict() for s in signals]
            })
    except Exception as e:
        logger.error(f"Error searching signals: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/signals/stats", methods=["GET"])
def get_signal_stats():
    """Get signal statistics."""
    try:
        with get_db_session() as session:
            total = session.query(Signal).count()
            categories = session.query(Signal.category).distinct().all()
            categories = [c[0] for c in categories if c[0]]

            return jsonify({
                "success": True,
                "total_signals": total,
                "categories": categories
            })
    except Exception as e:
        logger.error(f"Error getting signal stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/status", methods=["GET"])
def get_scan_status():
    """Get current scan status."""
    try:
        # TODO: Implement when advanced scanner is integrated
        return jsonify({
            "success": True,
            "is_scanning": False,
            "progress": None
        })
    except Exception as e:
        logger.error(f"Error getting scan status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/history", methods=["GET"])
def get_scan_history():
    """Get scan history."""
    try:
        limit = request.args.get("limit", type=int, default=20)
        # TODO: Implement when advanced scanner is integrated
        return jsonify({
            "success": True,
            "scans": []
        })
    except Exception as e:
        logger.error(f"Error getting scan history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/advanced", methods=["POST"])
def start_advanced_scan():
    """Start an advanced multi-band scan."""
    try:
        data = request.get_json() or {}
        bands = data.get("bands", [])
        # TODO: Implement when advanced scanner is integrated
        return jsonify({
            "success": False,
            "error": "Advanced scanning not yet implemented"
        }), 501
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scan/stop", methods=["POST"])
def stop_scan():
    """Stop current scan."""
    try:
        # TODO: Implement when advanced scanner is integrated
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error stopping scan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/tune_signal", methods=["POST"])
def tune_signal():
    """Smart tuning: tune to a signal and start audio with appropriate settings."""
    global current_device, audio_mode

    if not current_device or not current_device.is_connected:
        return jsonify({"success": False, "error": "No device connected"}), 400

    try:
        data = request.get_json()

        # Extract signal parameters
        frequency = data.get("frequency")
        bandwidth = data.get("bandwidth")
        modulation = data.get("modulation", "FM")

        if not frequency:
            return jsonify({"success": False, "error": "Frequency required"}), 400

        # Tune to frequency
        current_device.set_frequency(int(frequency))

        # Set bandwidth if provided and device supports it
        if bandwidth:
            try:
                current_device.set_bandwidth(int(bandwidth))
            except Exception as e:
                logger.warning(f"Could not set bandwidth: {e}")

        # Determine audio mode from modulation
        if "AM" in modulation.upper():
            audio_mode = "AM"
        elif "FM" in modulation.upper():
            audio_mode = "FM"
        else:
            audio_mode = "FM"  # Default

        # Start audio streaming
        response = start_audio()

        logger.info(f"Tuned to signal at {frequency/1e6:.3f} MHz ({modulation})")

        return response

    except Exception as e:
        logger.error(f"Error tuning to signal: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/classifications/label", methods=["POST"])
def label_signal():
    """Manually label a signal for training."""
    try:
        data = request.get_json()
        frequency = data.get("frequency")
        category = data.get("category")
        modulation = data.get("modulation")

        if not frequency or not category:
            return jsonify({"success": False, "error": "Frequency and category required"}), 400

        # Store manual label for future training
        # This would integrate with the data collection system
        logger.info(f"Manual label: {frequency} Hz -> {category} ({modulation})")

        return jsonify({"success": True, "message": f"Labeled {frequency} Hz as {category}"})

    except Exception as e:
        logger.error(f"Error labeling signal: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ml/train", methods=["POST"])
def train_model():
    """Train ML model from collected data."""
    try:
        from backend.ml.trainer import model_trainer

        data = request.get_json() or {}
        test_size = float(data.get("test_size", 0.2))
        n_estimators = int(data.get("n_estimators", 100))

        metrics = model_trainer.train_model(test_size=test_size, n_estimators=n_estimators)
        model_path = model_trainer.save_model()

        return jsonify(
            {
                "success": True,
                "metrics": metrics,
                "model_path": model_path,
            }
        )

    except ValueError as e:
        logger.error(f"Training error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ml/models", methods=["GET"])
def list_models():
    """List available trained models."""
    try:
        from backend.ml.trainer import model_trainer

        models = []
        for model_file in model_trainer.models_dir.glob("*.pkl"):
            metadata_file = model_file.with_name(model_file.stem + "_metadata.json")
            metadata = {}
            if metadata_file.exists():
                import json

                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

            models.append(
                {
                    "filename": model_file.name,
                    "path": str(model_file),
                    "metadata": metadata,
                }
            )

        return jsonify({"success": True, "models": models})

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ml/models/<model_name>/load", methods=["POST"])
def load_model(model_name: str):
    """Load a trained model."""
    try:
        from backend.ml.trainer import model_trainer

        model_path = model_trainer.models_dir / model_name
        if not model_path.exists():
            return jsonify({"success": False, "error": "Model not found"}), 404

        model_trainer.load_model(str(model_path))
        return jsonify({"success": True, "message": f"Loaded model: {model_name}"})

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# WebSocket Events
@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit("status", {"message": "Connected to AI-Radio server"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("join_room")
def handle_join_room(data):
    """Handle client joining a room."""
    room = data.get("room", "default")
    join_room(room)
    emit("status", {"message": f"Joined room: {room}"})


@socketio.on("leave_room")
def handle_leave_room(data):
    """Handle client leaving a room."""
    room = data.get("room", "default")
    leave_room(room)
    emit("status", {"message": f"Left room: {room}"})


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
            socketio.emit(
                "audio_samples",
                {
                    "samples": audio_data,
                    "sample_rate": audio_demodulator.audio_rate,
                    "mode": audio_mode,
                },
            )

            # Small sleep to prevent overwhelming the socket
            time.sleep(0.05)

        except Exception as e:
            logger.error(f"Error in audio worker: {e}")
            time.sleep(0.1)

    logger.info("Audio worker stopped")


def _process_stream_iteration() -> bool:
    """Process a single streaming iteration. Returns False to stop streaming."""
    global current_device, signal_processor, waterfall_processor

    # Check device health
    if not current_device or not current_device.is_connected:
        logger.warning("Device disconnected during streaming")
        socketio.emit(
            "device_error",
            {"error": "Device disconnected", "timestamp": datetime.now().isoformat()},
        )
        return False

    samples = current_device.read_samples(signal_processor.fft_size)
    if samples is None:
        return True  # Let caller handle error backoff

    freqs, spectrum = signal_processor.compute_fft(samples)
    waterfall_processor.add_spectrum(spectrum)
    signals = signal_processor.detect_signals(spectrum, current_device.frequency)
    features = signal_processor.extract_features(samples)

    for sig in signals[:10]:
        try:
            classification = signal_classifier.classify_signal(
                frequency=sig["frequency"], features=features, spectrum=spectrum, signal_info=sig
            )
            sig["category"] = classification.category
            sig["confidence"] = classification.confidence
            sig["modulation"] = classification.modulation
            sig["description"] = classification.description
            sig["technical_details"] = classification.technical_details

            # Store in database
            try:
                with get_db_session() as session:
                    signal_record = Signal(
                        frequency=sig["frequency"],
                        power=sig.get("power"),
                        bandwidth=sig.get("bandwidth"),
                        snr=sig.get("snr"),
                        timestamp=datetime.now().isoformat(),
                        category=classification.category,
                        modulation=classification.modulation,
                        confidence=classification.confidence,
                        description=classification.description,
                        technical_details=classification.technical_details,
                        sample_rate=current_device.sample_rate,
                        gain=current_device.gain,
                    )
                    session.add(signal_record)
                    signal_id = signal_record.id

                    classification_record = Classification(
                        signal_id=signal_id,
                        frequency=sig["frequency"],
                        category=classification.category,
                        confidence=classification.confidence,
                        modulation=classification.modulation,
                        timestamp=datetime.now().isoformat(),
                        features=features,
                        method="ml" if signal_classifier.use_ml else "rule_based",
                    )
                    session.add(classification_record)
            except Exception as db_error:
                logger.warning(f"Error storing signal in database: {db_error}")

        except Exception as e:
            logger.error(f"Error classifying signal: {e}")
            sig["category"] = "unknown"
            sig["confidence"] = 0.0
            sig["modulation"] = "Unknown"
            sig["description"] = "Unknown Signal"
            sig["technical_details"] = {}

    # Write samples to recording if active
    if recording_manager.is_recording:
        try:
            recording_manager.write_samples(samples)
        except Exception as e:
            logger.error(f"Error writing to recording: {e}")

    if np.random.rand() < 0.1:
        try:
            data_collector.add_sample(
                samples=samples,
                spectrum=spectrum,
                frequency=current_device.frequency,
                sample_rate=current_device.sample_rate,
                gain=current_device.gain,
                signals_detected=signals,
            )
        except Exception as e:
            logger.error(f"Error collecting data: {e}")

    center_freq = float(current_device.frequency)
    sample_rate = float(current_device.sample_rate)
    resolution_hz = float(signal_processor.get_frequency_resolution())
    abs_freqs = (freqs + center_freq).tolist()

    socketio.emit(
        "spectrum_data",
        {
            "frequencies": freqs.tolist(),
            "absolute_frequencies": abs_freqs,
            "center_frequency": center_freq,
            "sample_rate": sample_rate,
            "resolution_hz": resolution_hz,
            "spectrum": spectrum.tolist(),
            "signals": signals,
            "features": features,
            "timestamp": datetime.now().isoformat(),
        },
    )

    if int(time.time() * 10) % 5 == 0:
        waterfall_data = waterfall_processor.get_waterfall()
        socketio.emit(
            "waterfall_data",
            {"data": waterfall_data.tolist(), "timestamp": datetime.now().isoformat()},
        )

    time.sleep(0.1)
    return True


def streaming_worker():
    """Worker thread for real-time spectrum streaming."""
    global current_device, streaming_active

    logger.info("Starting streaming worker")
    consecutive_errors = 0
    max_consecutive_errors = 10

    while streaming_active:
        try:
            should_continue = _process_stream_iteration()
            if not should_continue:
                streaming_active = False
                break
            # Reset errors when iteration succeeds fully
            consecutive_errors = 0
        except Exception as e:
            logger.error(f"Error in streaming worker: {e}", exc_info=True)
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                logger.error("Too many consecutive errors, stopping stream")
                socketio.emit(
                    "device_error", {"error": str(e), "timestamp": datetime.now().isoformat()}
                )
                streaming_active = False
                break
            time.sleep(0.1)

    logger.info("Streaming worker stopped")


if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)

    # Run the application
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
