import time
from typing import Optional, Dict, Any

from backend.settings import get_settings


class OpenAIClient:
	"""Thin wrapper around OpenAI chat completions with retries/timeouts.

	This module deliberately avoids importing the SDK at import time to keep
	startup resilient when the key is missing; it loads lazily when used.
	"""

	def __init__(self, model: Optional[str] = None, timeout: float = 20.0, max_retries: int = 2):
		settings = get_settings()
		self.api_key = settings.get('openai_api_key')
		self.model = model or settings.get('openai_model', 'gpt-4o-mini')
		self.timeout = timeout
		self.max_retries = max_retries

	def parse_intent(self, user_text: str, system_prompt: str) -> Dict[str, Any]:
		"""Call OpenAI to parse a user command into a structured intent.

		Returns a dict with keys: intent, params, meta, and explanation.
		"""
		if not self.api_key:
			raise RuntimeError('OpenAI API key not configured')

		# Lazy import to avoid hard dependency if not configured
		from openai import OpenAI

		client = OpenAI(api_key=self.api_key)
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_text},
		]

		last_err: Optional[Exception] = None
		for attempt in range(self.max_retries + 1):
			try:
				resp = client.chat.completions.create(
					model=self.model,
					messages=messages,
					response_format={"type": "json_object"},
					temperature=0.2,
					max_tokens=400,
				)
				text = resp.choices[0].message.content or '{}'
				# Expect a JSON object; parse defensively
				import json
				parsed = json.loads(text)
				return parsed
			except Exception as e:
				last_err = e
				if attempt < self.max_retries:
					time.sleep(0.5 * (attempt + 1))
					continue
				raise


