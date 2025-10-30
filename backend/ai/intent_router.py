from typing import Any

from backend.config.targets import HYDROGEN_LINE_HZ
from backend.radio.scan_fm import scan_fm_band
from backend.radio.scan_noaa import scan_noaa


def execute_intent(intent_obj: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Execute parsed intent using provided context.

    ctx must provide: current_device, signal_processor, read_spectrum_fn, preset_manager
    """
    intent = intent_obj.get("intent")
    params = intent_obj.get("params", {})

    current_device = ctx["current_device"]
    signal_processor = ctx["signal_processor"]
    read_spectrum_fn = ctx["read_spectrum_fn"]
    preset_manager = ctx["preset_manager"]

    if intent == "STATUS":
        return {
            "success": True,
            "device_connected": bool(current_device and current_device.is_connected),
            "device_info": current_device.get_device_info() if current_device else None,
        }

    if not current_device or not current_device.is_connected:
        return {"success": False, "error": "No device connected"}

    if intent == "TUNE":
        freq = float(params["frequency_hz"])
        mode = str(params.get("mode", "FM"))
        bw = params.get("bandwidth_hz")
        ok = current_device.set_frequency(freq)
        if not ok:
            return {"success": False, "error": "Failed to set frequency"}
        if bw:
            try:
                current_device.set_bandwidth(float(bw))
            except Exception:
                pass
        return {"success": True, "frequency": freq, "mode": mode}

    if intent == "SCAN":
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

    if intent == "WEATHER_TUNE":
        results = scan_noaa(read_spectrum_fn)
        if not results:
            return {"success": False, "error": "No NOAA channel detected"}
        best = results[0]
        current_device.set_frequency(best["frequency"])
        return {"success": True, "tuned": best}

    if intent == "HYDROGEN_LINE_TUNE":
        current_device.set_frequency(HYDROGEN_LINE_HZ)
        # Narrow span, long integration is a UI concern; here we just tune
        return {"success": True, "frequency": HYDROGEN_LINE_HZ}

    if intent == "PRESET":
        name = params.get("name")
        preset = preset_manager.get_preset(name)
        if not preset:
            return {"success": False, "error": "Preset not found"}
        # Apply subset here; rely on existing preset endpoint normally
        current_device.set_frequency(preset.frequency)
        current_device.set_sample_rate(preset.sample_rate)
        current_device.set_gain(preset.gain)
        if preset.bandwidth:
            try:
                current_device.set_bandwidth(preset.bandwidth)
            except Exception:
                pass
        return {"success": True, "preset": preset.to_dict()}

    return {"success": False, "error": f"Unsupported intent: {intent}"}
