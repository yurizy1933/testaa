import json
import os
import re
import time
import ast
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI


BASE_DIR = os.path.dirname(__file__)
INPUT_PATH = os.path.join(BASE_DIR, 'jsonlData', 'flase.jsonl')
OUTPUT_PATH = os.path.join(BASE_DIR, 'jsonlData', 'review.jsonl')

# DeepSeek API configuration (env-overridable)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-ae89b4e492104945ae83c6a2647410c9')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL_ID = os.environ.get('DEEPSEEK_MODEL_ID', '')

RATE_LIMIT_SLEEP_SEC = float(os.environ.get('REVIEW_RATE_LIMIT_SLEEP_SEC', '0.4'))
RETRIES = int(os.environ.get('REVIEW_RETRIES', '3'))
RETRY_BACKOFF_SEC = float(os.environ.get('RETRY_BACKOFF_SEC', '0.8'))


def init_deepseek_client_and_model() -> Tuple[OpenAI, str]:
	client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
	model_id = DEEPSEEK_MODEL_ID
	if not model_id:
		models = client.models.list().data
		candidate = None
		for m in models:
			mid = getattr(m, 'id', '') or ''
			if 'deepseek' in str(mid).lower():
				candidate = mid
				break
		model_id = candidate or models[0].id
	return client, model_id


def extract_requirement_text(messages: List[Dict[str, Any]]) -> str:
	"""
	Try to extract the substring between "完整需求内容为：" and "，测试模块为" from the last user message containing it.
	Fallback: return the last user message's content.
	"""
	candidate = ''
	for m in reversed(messages):
		if m.get('role') == 'user':
			content = m.get('content') or ''
			if '完整需求内容为：' in content:
				match = re.search(r'完整需求内容为：(.+?)，测试模块为', content, re.S)
				if match:
					return match.group(1).strip()
				candidate = content
				break
	return candidate


def extract_test_module(messages: List[Dict[str, Any]]) -> str:
	for m in reversed(messages):
		if m.get('role') == 'user':
			content = m.get('content') or ''
			md = re.search(r'测试模块为：(.+?)(?:，|,|。|\n)', content)
			if md:
				return md.group(1).strip()
	return ''


def extract_test_direction(messages: List[Dict[str, Any]]) -> str:
	for m in reversed(messages):
		if m.get('role') == 'user':
			content = m.get('content') or ''
			md = re.search(r'测试方向为：(.+?)(?:，指定需要|。|,|\n)', content)
			if md:
				return md.group(1).strip()
	return ''


def extract_testpoints_from_assistant(assistant_text: str) -> List[str]:
	"""
	Assistant often outputs Python-like list of dicts. Try JSON first, then ast.literal_eval.
	Collect 'testpoint' fields if present, else return empty list.
	"""
	if not assistant_text:
		return []
	text = assistant_text.strip()
	data = None
	# Try JSON
	try:
		data = json.loads(text)
	except Exception:
		pass
	# Try Python literal
	if data is None:
		try:
			data = ast.literal_eval(text)
		except Exception:
			return []
	# Normalize to list
	items: List[Dict[str, Any]] = []
	if isinstance(data, list):
		items = data
	elif isinstance(data, dict):
		items = [data]
	else:
		return []
	result: List[str] = []
	for it in items:
		if isinstance(it, dict) and 'testpoint' in it:
			val = it.get('testpoint')
			if isinstance(val, str):
				result.append(val.strip())
	return result


def build_review_prompt(requirement_text: str, test_module: str, test_direction: str, testpoints: List[str]) -> List[Dict[str, str]]:
	sys_msg = {
		"role": "system",
		"content": (
			"你是资深软件测试专家。现在给你一个需求内容、对应的测试模块、测试方向，以及若干测试用例的测试点(testpoint)。"
			"只需判断：这些测试点是否覆盖了需求的所有核心测试点，且没有新编造的测试结果/结论。"
			"严格仅回答 YES 或 NO，不要输出其他任何内容。"
		)
	}
	user_msg = {
		"role": "user",
		"content": (
			f"需求内容:\n{requirement_text}\n\n"
			f"测试模块: {test_module}\n"
			f"测试方向: {test_direction}\n\n"
			f"测试点列表(testpoint):\n- " + "\n- ".join(testpoints)
		)
	}
	return [sys_msg, user_msg]


def deepseek_review(client: OpenAI, model_id: str, requirement_text: str, test_module: str, test_direction: str, testpoints: List[str]) -> Dict[str, Any]:
	messages = build_review_prompt(requirement_text, test_module, test_direction, testpoints)
	last_err: Optional[Exception] = None
	for attempt in range(RETRIES):
		try:
			resp = client.chat.completions.create(
				model=model_id,
				messages=messages,
				temperature=0,
				max_tokens=8,
				stop=None,
			)
			content = (resp.choices[0].message.content or '').strip()
			answer = re.sub(r'^```[a-zA-Z]*\n|\n```$', '', content).strip().upper()
			if 'YES' in answer and 'NO' not in answer:
				return {"ok": True, "boolean": True, "raw": content}
			if 'NO' in answer and 'YES' not in answer:
				return {"ok": True, "boolean": False, "raw": content}
			# ambiguous
			return {"ok": False, "error": "AMBIGUOUS", "raw": content}
		except Exception as e:
			last_err = e
			time.sleep(RETRY_BACKOFF_SEC * (2 ** attempt))
	return {"ok": False, "error": f"API_ERROR: {last_err}"}


def process_false_jsonl(input_path: str = INPUT_PATH, output_path: str = OUTPUT_PATH) -> Dict[str, int]:
	client, model_id = init_deepseek_client_and_model()
	stats = {"processed": 0, "written": 0, "errors": 0}
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	with open(input_path, 'r', encoding='utf-8') as fin, open(output_path, 'w', encoding='utf-8') as fout:
		for idx, line in enumerate(fin, start=1):
			line = line.strip()
			if not line:
				continue
			stats["processed"] += 1
			try:
				obj = json.loads(line)
				messages = obj.get('messages') or []
				assistant_text = ''
				for m in reversed(messages):
					if m.get('role') == 'assistant':
						assistant_text = m.get('content') or ''
						break
				requirement = extract_requirement_text(messages)
				test_module = extract_test_module(messages)
				test_direction = extract_test_direction(messages)
				testpoints = extract_testpoints_from_assistant(assistant_text)
				review = deepseek_review(client, model_id, requirement, test_module, test_direction, testpoints)
				# Only when DeepSeek says NO -> write the original line exactly
				if review.get("ok") and review.get("boolean") is False:
					fout.write(line + "\n")
					stats["written"] += 1
				time.sleep(RATE_LIMIT_SLEEP_SEC)
			except Exception as e:
				stats["errors"] += 1
				fout.write(json.dumps({"line": idx, "error": str(e)}, ensure_ascii=False) + "\n")
	return stats


if __name__ == '__main__':
	res = process_false_jsonl()
	print(json.dumps(res, ensure_ascii=False, indent=2))


