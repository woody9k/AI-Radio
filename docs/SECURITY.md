# Security

## Keys & Secrets
- Never commit secrets.
- Store OpenAI key via Settings UI or environment variable.
- Keys are masked in API responses.

## Network Exposure
- Dev frontend binds to `0.0.0.0`. Use on trusted networks only.
- Restrict CORS in production (dev uses `*`).

## Data Privacy
- Do not send raw IQ/spectrum to LLM. Only send text and band maps.

## Rate Limiting & Abuse
- Avoid rapid retune/scan loops. Backend should debounce device reconfig.
