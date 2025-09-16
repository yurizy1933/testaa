import json
import os
import time
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI


DATA_PATH = os.path.join(os.path.dirname(__file__), 'jsonlData', 'new_train_02.jsonl')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'jsonlData', 'flase.jsonl')
ERROR_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'jsonlData', 'errors.jsonl')

# Configuration for model calling
DEFAULT_MODEL = os.environ.get('EVAL_MODEL', 'auto')
RATE_LIMIT_SLEEP_SEC = float(os.environ.get('EVAL_RATE_LIMIT_SLEEP_SEC', '0.5'))
EVAL_RETRIES = int(os.environ.get('EVAL_RETRIES', '3'))
EVAL_RETRY_BACKOFF_SEC = float(os.environ.get('EVAL_RETRY_BACKOFF_SEC', '1.0'))

# Local gateway clients/models (separated for generation and deepseek judge)
_GEN_CLIENT: Optional[OpenAI] = None
_GEN_MODEL_ID: Optional[str] = None
_DS_CLIENT: Optional[OpenAI] = None
_DEEPSEEK_MODEL_ID: Optional[str] = None

# DeepSeek official API configuration (env overrideable)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-ae89b4e492104945ae83c6a2647410c9')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')


def _ensure_gen_client_and_model() -> tuple:
	"""
	Initialize generation client/model with optional env overrides.
	Env:
	- GEN_BASE_URL (default: 'http://36.138.60.239:31687/v1')
	- GEN_MODEL_ID (optional; fallback to first model)
	"""
	global _GEN_CLIENT, _GEN_MODEL_ID
	if _GEN_CLIENT is None:
		base_url = os.environ.get('GEN_BASE_URL', 'http://36.138.60.239:31496/v1')
		_GEN_CLIENT = OpenAI(
			api_key='EMPTY',
			base_url=base_url,
		)
	if _GEN_MODEL_ID is None:
		model_from_env = os.environ.get('GEN_MODEL_ID')
		if model_from_env:
			_GEN_MODEL_ID = model_from_env
		else:
			_GEN_MODEL_ID = _GEN_CLIENT.models.list().data[0].id
	return _GEN_CLIENT, _GEN_MODEL_ID


def _ensure_deepseek_client_and_model() -> tuple:
	"""
	Initialize deepseek judge client/model with official DeepSeek API.
	Env overrides:
	- DEEPSEEK_API_KEY (default from code)
	- DEEPSEEK_BASE_URL (default: https://api.deepseek.com)
	- DEEPSEEK_MODEL_ID (optional; fallback to first model that contains 'deepseek' or first overall)
	"""
	global _DS_CLIENT, _DEEPSEEK_MODEL_ID
	if _DS_CLIENT is None:
		_DS_CLIENT = OpenAI(
			api_key=DEEPSEEK_API_KEY,
			base_url=DEEPSEEK_BASE_URL,
		)
	if _DEEPSEEK_MODEL_ID is None:
		model_from_env = os.environ.get('DEEPSEEK_MODEL_ID')
		if model_from_env:
			_DEEPSEEK_MODEL_ID = model_from_env
		else:
			models = _DS_CLIENT.models.list().data
			candidate = None
			for m in models:
				mid = getattr(m, 'id', '') or ''
				if 'deepseek' in str(mid).lower():
					candidate = mid
					break
			_DEEPSEEK_MODEL_ID = candidate or models[0].id
	return _DS_CLIENT, _DEEPSEEK_MODEL_ID


def judge_equivalence_with_deepseek(gold: str, pred: str) -> Optional[bool]:
	"""
	Use a deepseek model to judge if pred semantically matches gold.
	Return True/False, or None if deepseek model not available or on error.
	"""
	client, deepseek_id = _ensure_deepseek_client_and_model()
	if not deepseek_id:
		return None
	try:
		messages = [
			{"role": "system", "content": "你是一个严格的一致性判定器。判断两个中文答案是否等价，只回答 YES 或 NO。不要输出其他任何内容。"},
			{"role": "user", "content": f"原答案：\n{gold}\n\n新答案：\n{pred}\n\n问题：两者在语义和关键信息上是否等价？只回答 YES 或 NO。"},
		]
		resp = client.chat.completions.create(
			model=deepseek_id,
			messages=messages,
			temperature=0,
			max_tokens=4,
			top_p=1.0,
		)
		answer = (resp.choices[0].message.content or '').strip().upper()
		if 'YES' in answer and 'NO' not in answer:
			return True
		if 'NO' in answer and 'YES' not in answer:
			return False
		# fallback heuristic on ambiguous output
		return True if answer == 'YES' else False if answer == 'NO' else None
	except Exception:
		return None


def normalize_text(text: str) -> str:
	"""
	Normalize text for comparison: strip, lowercase, collapse whitespace and punctuation spaces.
	"""
	if text is None:
		return ''
	n = text.strip().lower()
	# Remove all whitespace characters
	n = re.sub(r"\s+", "", n)
	# Normalize some Chinese punctuation variants (keep it simple)
	n = n.replace('，', ',').replace('。', '.').replace('：', ':').replace('；', ';').replace('！', '!').replace('？', '?')
	return n


def extract_gold_answer(messages: List[Dict[str, Any]]) -> Optional[str]:
	"""
	Assume the last assistant message is the gold answer.
	"""
	for m in reversed(messages):
		if m.get('role') == 'assistant':
			return m.get('content', '')
	return None


def strip_last_assistant(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	result: List[Dict[str, Any]] = []
	removed = False
	for m in reversed(messages):
		if (m.get('role') == 'assistant') and not removed:
			removed = True
			continue
		result.append(m)
	return list(reversed(result))


def call_model(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
	"""
	Call the chat model with given messages and return assistant content.
	Includes retry with exponential backoff for transient errors.
	"""
	client, resolved_model = _ensure_gen_client_and_model()
	last_err: Optional[Exception] = None
	for attempt in range(EVAL_RETRIES):
		try:
			resp = client.chat.completions.create(
				model=resolved_model,
				messages=messages,
				temperature=0.2,
				max_tokens=2048,
				top_p=1.0,
			)
			choice = resp.choices[0]
			return choice.message.content or ''
		except Exception as e:
			last_err = e
			# Backoff then retry
			time.sleep(EVAL_RETRY_BACKOFF_SEC * (2 ** attempt))
	# If still failing, raise
	raise RuntimeError(f"GEN_API_ERROR: {last_err}")


def reevaluate_dataset(
	input_path: str = DATA_PATH,
	output_path: str = OUTPUT_PATH,
	model: str = DEFAULT_MODEL,
	max_samples: Optional[int] = None,
) -> Dict[str, int]:
	"""
	Re-ask the model for each record. If new answer != original, write updated record
	(with new assistant content and label=false) to output_path (jsonl).
	Returns simple stats.
	"""
	processed = 0
	skipped_equal = 0
	mismatches = 0
	errors = 0

	# Ensure output directory exists
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	os.makedirs(os.path.dirname(ERROR_OUTPUT_PATH), exist_ok=True)

	with open(input_path, 'r', encoding='utf-8') as fin, open(output_path, 'w', encoding='utf-8') as fout, open(ERROR_OUTPUT_PATH, 'w', encoding='utf-8') as ferr:
		for line in fin:
			if max_samples is not None and processed >= max_samples:
				break
			line = line.strip()
			if not line:
				continue
			processed += 1
			try:
				record = json.loads(line)
				messages = record.get('messages')
				if not isinstance(messages, list):
					raise ValueError('messages is not a list')

				gold = extract_gold_answer(messages) or ''
				prompt_messages = strip_last_assistant(messages)

				# Call model with retry; on failure, log to error file and skip
				try:
					new_answer = call_model(prompt_messages, model=model)
				except Exception as api_err:
					errors += 1
					ferr.write(json.dumps({"error": str(api_err), "raw": record}, ensure_ascii=False) + "\n")
					# Respect rate limiting even on error
					time.sleep(RATE_LIMIT_SLEEP_SEC)
					continue

				# Prefer deepseek semantic judge; fallback to normalization
				is_same = judge_equivalence_with_deepseek(gold, new_answer)
				if is_same is None:
					is_same = normalize_text(new_answer) == normalize_text(gold)
				if is_same:
					skipped_equal += 1
				else:
					mismatches += 1
					# Replace last assistant content with new answer; if none exists, append
					updated_messages = list(messages)
					# Find last assistant index
					idx = None
					for i in range(len(updated_messages) - 1, -1, -1):
						if updated_messages[i].get('role') == 'assistant':
							idx = i
							break
					if idx is not None:
						updated_messages[idx] = {"role": "assistant", "content": new_answer}
					else:
						updated_messages.append({"role": "assistant", "content": new_answer})

					out_obj = {
						"messages": updated_messages,
						"label": False,
					}
					fout.write(json.dumps(out_obj, ensure_ascii=False) + "\n")

				# Rate limit protection
				time.sleep(RATE_LIMIT_SLEEP_SEC)
			except Exception as e:
				errors += 1
				# Also persist the error case so it can be inspected later
				try:
					fallback_obj = {
						"error": str(e),
						"raw": line,
						"label": False,
					}
					ferr.write(json.dumps(fallback_obj, ensure_ascii=False) + "\n")
				except Exception:
					pass

	return {
		"processed": processed,
		"equal": skipped_equal,
		"mismatches": mismatches,
		"errors": errors,
	}


def test():
    client = OpenAI(
        api_key='EMPTY',
        base_url=f'http://36.138.60.239:31496/v1/',
    )
    model = client.models.list().data[0].id
    print(f'model: {model}')

    messages = [{'role': 'user', 'content': '你是谁'}]

    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=512, temperature=0)
    query = messages[0]['content']
    response = resp.choices[0].message.content
    print(f'query: {query}')
    print(f'response: {response}')

if __name__ == '__main__':
	# Not a CLI; provide a simple entry point when run directly.
	stats = reevaluate_dataset()
	print(json.dumps(stats, ensure_ascii=False, indent=2))
	# test()
