# Troubleshooting Guide

## Common Issues and Solutions

### Issue: Spectrum Display Freezes After 1-2 Minutes

**Symptoms:**
- Spectrum display stops updating
- Browser UI becomes unresponsive
- Device shows as disconnected after refresh

**Causes:**
- Backend crashed due to RTL-SDR read errors
- Too many signals being classified (performance bottleneck)
- Data collection overhead
- Memory leaks from unbounded buffers

**Fixes Applied:**
1. **Better Error Handling**: Streaming worker now tracks consecutive errors and gracefully stops after 10 failures
2. **Signal Limiting**: Only classify first 10 detected signals per frame to prevent slowdown
3. **Data Collection Sampling**: Only collect ML training data 10% of the time to reduce overhead
4. **Device Health Checks**: Worker now checks device connection status each loop
5. **Error Recovery**: Frontend receives `device_error` events and updates UI accordingly

### Issue: Device Shows Disconnected After Browser Refresh

**Symptoms:**
- After refreshing browser, UI shows "No devices found"
- Backend actually has device connected

**Causes:**
- Frontend state lost on refresh
- No synchronization between backend and frontend state
- No health monitoring

**Fixes Applied:**
1. **Health Check Endpoint**: New `/api/health` endpoint reports device and streaming status
2. **Frontend Polling**: Frontend polls health endpoint every 5 seconds
3. **Auto-Sync**: If backend reports device connected but frontend doesn't know, it automatically fetches devices
4. **Disconnect Detection**: If backend loses device, frontend is notified and updates UI

### Issue: Backend Crashes Silently

**Symptoms:**
- Backend process stops running
- Frontend loses connection
- No error messages visible

**Causes:**
- Unhandled exceptions in streaming worker
- RTL-SDR device errors (busy, disconnected, read failures)
- Memory leaks or resource exhaustion

**Fixes Applied:**
1. **Exception Logging**: All exceptions now logged with full traceback (`exc_info=True`)
2. **Graceful Degradation**: Errors no longer crash the worker, it continues or stops gracefully
3. **Device Error Events**: WebSocket `device_error` events notify frontend of issues
4. **Consecutive Error Tracking**: After 10 consecutive errors, worker stops and notifies user

### Issue: RTL-SDR Device Busy (Error -6)

**Symptoms:**
- `usb_claim_interface error -6`
- Cannot connect to device
- Device claimed by another process

**Solutions:**

**Quick Fix:**
```bash
./quick_kill_rtlsdr.sh
```

**Interactive Fix (with confirmation):**
```bash
./kill_rtlsdr_processes.sh
```

**Manual Fix:**
```bash
# Find processes using RTL-SDR
lsof | grep rtlsdr
ps aux | grep rtl

# Kill specific process
kill -9 <PID>

# Or kill all Python processes
pkill -9 python
```

### Performance Optimization

The following changes improve performance and stability:

1. **Signal Classification Limit**: Only first 10 signals classified per frame
2. **Data Collection Sampling**: ML data collected at 10% rate (was 100%)
3. **Reduced Logging**: Removed per-signal classification logs
4. **Error Throttling**: 100ms delay on errors to prevent CPU spinning
5. **Memory Bounds**: Classification history limited to 1000 entries

### Monitoring Backend Health

**Check if backend is running:**
```bash
ps aux | grep "python backend/app.py"
```

**View backend logs:**
```bash
tail -f backend_output.log
```

**Check for errors:**
```bash
grep ERROR backend_output.log
```

**Test health endpoint:**
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "success": true,
  "device_connected": true,
  "streaming": false,
  "timestamp": "2025-10-16T19:23:42.123456"
}
```

### Restarting Services

**Full restart:**
```bash
# Kill RTL-SDR processes
./quick_kill_rtlsdr.sh

# Kill backend
pkill -f "python backend/app.py"

# Start backend
cd /home/bwoodward/Code/AI-Radio
source venv/bin/activate
python backend/app.py > backend_output.log 2>&1 &

# Frontend should auto-reconnect
```

### Debug Mode

To see more detailed logs, edit `backend/app.py`:

```python
# Change from INFO to DEBUG
logging.basicConfig(level=logging.DEBUG)
```

Then restart the backend.

### Best Practices

1. **Always kill RTL-SDR processes before starting backend**
2. **Monitor backend logs when testing new features**
3. **Use health check endpoint to verify backend state**
4. **Don't refresh browser while streaming is active** (stop streaming first)
5. **Check USB connection if device repeatedly disconnects**

### Known Limitations

1. **Maximum 10 signals classified per frame** - More signals will be detected but not classified
2. **10% data collection rate** - Not all samples saved for ML training
3. **Waterfall limited to 100 rows** - Older data scrolls off
4. **Classification history limited to 1000 entries** - Oldest entries discarded

These limits are intentional to prevent performance degradation and memory leaks.

