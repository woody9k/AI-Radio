export async function sendAICommand(text, { dryRun = false } = {}) {
	const res = await fetch('/api/ai/command', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ text, dry_run: dryRun })
	});
	return await res.json();
}

export async function getAISettings() {
	const res = await fetch('/api/settings/ai');
	return await res.json();
}

export async function saveAISettings(payload) {
	const res = await fetch('/api/settings/ai', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	return await res.json();
}


