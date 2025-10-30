from typing import Any

from backend.config.targets import HYDROGEN_LINE_HZ
from backend.radio.scan_fm import scan_fm_band
from backend.radio.scan_noaa import scan_noaa


def _status_response(current_device) -> dict[str, Any]:
    return {
        "success": True,
        "device_connected": bool(current_device and current_device.is_connected),
        "device_info": current_device.get_device_info() if current_device else None,
    }


def _handle_tune(params: dict[str, Any], current_device) -> dict[str, Any]:
    freq = float(params["frequency_hz"])
    mode = str(params.get("mode", "FM"))
    bw = params.get("bandwidth_hz")
    if not current_device.set_frequency(freq):
        return {"success": False, "error": "Failed to set frequency"}
    if bw:
        try:
            current_device.set_bandwidth(float(bw))
        except Exception:
            # Best-effort bandwidth
            pass
    return {"success": True, "frequency": freq, "mode": mode}


def _handle_scan(params: dict[str, Any], read_spectrum_fn) -> dict[str, Any]:
    band = params.get("band", "fm")
    if band == "fm":
        stations = scan_fm_band(
            read_spectrum_fn,
            dwell_ms=int(params.get("dwell_ms", 200)),
            threshold_db=float(params.get("threshold_db", 12)),
        )
        return {"success": True, "results": stations}
    if band == "noaa":
        results = scan_noaa(read_spectrum_fn)
        return {"success": True, "results": results}
    return {"success": False, "error": f"Unsupported band: {band}"}


def _handle_weather_tune(current_device, read_spectrum_fn) -> dict[str, Any]:
    results = scan_noaa(read_spectrum_fn)
    if not results:
        return {"success": False, "error": "No NOAA channel detected"}
    best = results[0]
    current_device.set_frequency(best["frequency"])
    return {"success": True, "tuned": best}


def _handle_hydrogen_line_tune(current_device) -> dict[str, Any]:
    current_device.set_frequency(HYDROGEN_LINE_HZ)
    return {"success": True, "frequency": HYDROGEN_LINE_HZ}


def _handle_preset(params: dict[str, Any], current_device, preset_manager) -> dict[str, Any]:
    name = params.get("name")
    preset = preset_manager.get_preset(name)
    if not preset:
        return {"success": False, "error": "Preset not found"}
    current_device.set_frequency(preset.frequency)
    current_device.set_sample_rate(preset.sample_rate)
    current_device.set_gain(preset.gain)
    if preset.bandwidth:
        try:
            current_device.set_bandwidth(preset.bandwidth)
        except Exception:
            pass
    return {"success": True, "preset": preset.to_dict()}


def execute_intent(intent_obj: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Execute parsed intent using provided context.

    ctx must provide: current_device, signal_processor, read_spectrum_fn, preset_manager
    """
    intent = intent_obj.get("intent")
    params = intent_obj.get("params", {})

    current_device = ctx["current_device"]
    read_spectrum_fn = ctx["read_spectrum_fn"]
    preset_manager = ctx["preset_manager"]

    if intent == "STATUS":
        return _status_response(current_device)

    if not current_device or not current_device.is_connected:
        return {"success": False, "error": "No device connected"}

    if intent == "TUNE":
        return _handle_tune(params, current_device)
    if intent == "SCAN":
        return _handle_scan(params, read_spectrum_fn)
    if intent == "WEATHER_TUNE":
        return _handle_weather_tune(current_device, read_spectrum_fn)
    if intent == "HYDROGEN_LINE_TUNE":
        return _handle_hydrogen_line_tune(current_device)
    if intent == "PRESET":
        return _handle_preset(params, current_device, preset_manager)

    return {"success": False, "error": f"Unsupported intent: {intent}"}
