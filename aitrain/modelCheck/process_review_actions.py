import json
import os
import re
import ast
from typing import List, Dict, Any


BASE_DIR = os.path.dirname(__file__)
INPUT_PATH = os.path.join(BASE_DIR, 'jsonlData', 'review.jsonl')
TRAIN_OUT_PATH = os.path.join(BASE_DIR, 'jsonlData', 'trainning_02.jsonl')


def extract_requirement(messages: List[Dict[str, Any]]) -> str:
	req = ''
	for m in reversed(messages):
		if m.get('role') == 'user':
			content = m.get('content') or ''
			if '完整需求内容为：' in content:
				match = re.search(r'完整需求内容为：(.+?)，测试模块为', content, re.S)
				if match:
					return match.group(1).strip()
				req = content
				break
	return req


def extract_test_direction(messages: List[Dict[str, Any]]) -> str:
	for m in reversed(messages):
		if m.get('role') == 'user':
			content = m.get('content') or ''
			md = re.search(r'测试方向为：(.+?)(?:，指定需要|。|,|\n)', content)
			if md:
				return md.group(1).strip()
	return ''


def parse_assistant_cases(assistant_text: str) -> List[Dict[str, str]]:
	if not assistant_text:
		return []
	text = assistant_text.strip()
	data = None
	try:
		data = json.loads(text)
	except Exception:
		pass
	if data is None:
		try:
			data = ast.literal_eval(text)
		except Exception:
			return []
	items: List[Dict[str, Any]] = []
	if isinstance(data, list):
		items = data
	elif isinstance(data, dict):
		items = [data]
	else:
		return []
	cases: List[Dict[str, str]] = []
	for it in items:
		if not isinstance(it, dict):
			continue
		cases.append({
			"testpoint": str(it.get('testpoint', '') or ''),
			"operation": str(it.get('operation', '') or ''),
			"expectedresult": str(it.get('expectedresult', '') or ''),
		})
	return cases


def iterate_review(input_path: str = INPUT_PATH, out_path: str = TRAIN_OUT_PATH) -> None:
	if not os.path.exists(input_path):
		print(f'review file not found: {input_path}')
		return
	os.makedirs(os.path.dirname(out_path), exist_ok=True)
	with open(input_path, 'r', encoding='utf-8') as fin, open(out_path, 'a', encoding='utf-8') as fout:
		for idx, line in enumerate(fin, start=1):
			raw = line.rstrip('\n')
			if not raw.strip():
				continue
			try:
				obj = json.loads(raw)
				messages = obj.get('messages') or []
				assistant_text = ''
				for m in reversed(messages):
					if m.get('role') == 'assistant':
						assistant_text = m.get('content') or ''
						break
				req = extract_requirement(messages)
				direction = extract_test_direction(messages)
				cases = parse_assistant_cases(assistant_text)
				print(f'--- 第{idx}条 ---')
				print(f'需求: {req}')
				print(f'测试方向: {direction}')
				for ci, c in enumerate(cases, start=1):
					print(f'用例{ci}:')
					print(f'  测试点: {c.get("testpoint","")}')
					print(f'  操作: {c.get("operation","")}')
					print(f'  预期结果: {c.get("expectedresult","")}')
				user_in = input('是否通过?(true/false): ').strip().lower()
				if user_in == 'false':
					fout.write(raw + '\n')
			except Exception as e:
				print(f'解析第{idx}条失败: {e}')


if __name__ == '__main__':
	iterate_review()


