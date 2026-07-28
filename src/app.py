'''Ứng dụng tích hợp Chatbot Baseline và Cupid ReAct Agent.'''

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from queue import Empty, Queue
from threading import Thread
from typing import Any

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from prompts import (
    CHATBOT_BASELINE_PROMPT,
    MAX_ITERATIONS,
    REACT_SYSTEM_PROMPT,
    TIMEOUT_SECONDS,
)
from providers import get_llm_provider
from tools import AVAILABLE_TOOLS

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_PATH = os.path.join(PROJECT_ROOT, 'config', 'test_cases.json')
PROFILES_PATH = os.path.join(PROJECT_ROOT, 'cupid_data', 'cupid_profiles.json')


def _load_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def load_test_cases() -> list[dict[str, Any]]:
    tests = _load_json(TEST_CASES_PATH)
    if not isinstance(tests, list):
        raise ValueError('config/test_cases.json phải chứa một JSON array')
    return tests


def load_mock_profiles() -> list[dict[str, Any]]:
    profiles = _load_json(PROFILES_PATH)
    if not isinstance(profiles, list):
        raise ValueError('cupid_profiles.json phải chứa một JSON array')
    return profiles


def run_baseline_chatbot(user_query: str, provider) -> str:
    '''Chạy một LLM call với mock data trong context và không gọi tool.'''
    grounded_query = user_query + '\n\nMOCK_PROFILES:\n' + json.dumps(
        load_mock_profiles(), ensure_ascii=False
    )
    return provider.generate(
        grounded_query,
        system_prompt=CHATBOT_BASELINE_PROMPT,
    )


def _error(code: str, message: str) -> dict[str, Any]:
    return {'ok': False, 'error': {'code': code, 'message': message}}


def parse_react_response(response: str) -> dict[str, Any]:
    '''Parse đúng một Action hoặc Final Answer mà không dùng eval.'''
    if not isinstance(response, str) or not response.strip():
        return _error('INVALID_ACTION', 'Provider trả về nội dung rỗng')

    text = response.strip()
    if text.startswith('```') and text.endswith('```'):
        fenced = re.fullmatch(
            r'```(?:text|json|markdown)?\s*(.*?)\s*```',
            text,
            re.I | re.S,
        )
        if fenced:
            text = fenced.group(1).strip()

    final_match = re.fullmatch(r'Final Answer\s*:\s*(.+)', text, re.I | re.S)
    if final_match:
        return {
            'ok': True,
            'type': 'final',
            'answer': final_match.group(1).strip(),
        }

    action_match = re.fullmatch(
        r'Action\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\n'
        r'Action Input\s*:\s*(\{.*\})\s*',
        text,
        re.I | re.S,
    )
    if not action_match:
        return _error(
            'INVALID_ACTION',
            'Phản hồi phải chứa Action và Action Input, hoặc Final Answer',
        )

    try:
        action_input = json.loads(action_match.group(2))
    except json.JSONDecodeError:
        return _error('INVALID_ACTION', 'Action Input không phải JSON hợp lệ')
    if not isinstance(action_input, dict):
        return _error('INVALID_ACTION', 'Action Input phải là JSON object')

    return {
        'ok': True,
        'type': 'action',
        'action': action_match.group(1),
        'action_input': action_input,
    }


def execute_tool(action: str, action_input: dict[str, Any]) -> dict[str, Any]:
    '''Chỉ thực thi tool có trong registry và chuẩn hóa lỗi tích hợp.'''
    tool = AVAILABLE_TOOLS.get(action)
    if tool is None:
        return _error('UNKNOWN_TOOL', f'Tool không tồn tại: {action}')

    outcome: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def invoke() -> None:
        try:
            outcome.put(('result', tool(**action_input)))
        except TypeError:
            outcome.put(('invalid_arguments', None))
        except Exception:
            outcome.put(('execution_error', None))

    worker = Thread(target=invoke, daemon=True)
    worker.start()
    worker.join(TIMEOUT_SECONDS)
    if worker.is_alive():
        return _error(
            'TOOL_TIMEOUT',
            f'Tool vượt quá thời gian chờ {TIMEOUT_SECONDS} giây',
        )

    try:
        outcome_type, payload = outcome.get_nowait()
    except Empty:
        return _error('TOOL_EXECUTION_ERROR', 'Không thể thực thi tool')
    if outcome_type == 'invalid_arguments':
        return _error('INVALID_TOOL_ARGUMENTS', 'Tham số gọi tool không hợp lệ')
    if outcome_type == 'execution_error':
        return _error('TOOL_EXECUTION_ERROR', 'Không thể thực thi tool')
    if not isinstance(payload, dict) or 'ok' not in payload:
        return _error('TOOL_EXECUTION_ERROR', 'Tool trả về sai contract')
    return payload


def _provider_error(response: str) -> bool:
    if not isinstance(response, str):
        return True

    prefix = response.lstrip()
    header = re.match(r'^\[([^\]]+)\]', prefix)
    if not header:
        return False

    return bool(
        re.search(
            r'\b(error|exception)\b',
            header.group(1),
            re.I,
        )
    )


def _build_react_prompt(
    user_query: str,
    trace: list[dict[str, Any]],
    user_id: str | None = None,
) -> str:
    parts = [f'Yêu cầu ban đầu:\n{user_query}']
    if user_id:
        parts.append(f'Hồ sơ người dùng đã chọn: {user_id}')
    if trace:
        parts.append('Lịch sử Action và Observation đã được hệ thống xác minh:')
        for item in trace:
            parts.extend(
                [
                    'Action: {}'.format(item['action']),
                    'Action Input: '
                    + json.dumps(item['action_input'], ensure_ascii=False),
                    'Observation: '
                    + json.dumps(item['observation'], ensure_ascii=False),
                ]
            )
    parts.append('Hãy trả về Action tiếp theo hoặc Final Answer đúng contract.')
    return '\n\n'.join(parts)


def _collect_structured_output(
    result: dict[str, Any],
    action: str,
    observation: dict[str, Any],
) -> None:
    if not observation.get('ok'):
        return
    data = observation.get('data', {})
    if action == 'find_candidate_matches':
        result['matches'] = data.get('matches', [])
    elif action == 'calculate_compatibility':
        result['compatibility'] = data
    elif action == 'suggest_first_message':
        result['opener'] = data
    elif action == 'get_user_profile':
        result['profile'] = data


def _required_actions(
    user_query: str,
    user_id: str | None = None,
) -> list[str]:
    '''Xác định các tool tối thiểu cho yêu cầu thao tác trên hồ sơ cụ thể.'''
    query = user_query.lower()
    has_profile_context = (
        user_id is not None
        or re.search(r'\bu\d{3,}\b', query, re.I) is not None
    )
    if not has_profile_context:
        return []

    required = []
    find_patterns = (
        r'\btìm\b.*\b(người|ứng viên|hồ sơ)\b',
        r'\b(đề xuất|gợi ý)\b.*\b(người|ứng viên|hồ sơ)\b',
        r'\bghép đôi\b',
        r'\b(ai|người nào|hồ sơ nào)\b.*\b(phù hợp|hợp)\b',
        r'\b(phù hợp nhất|top\s*3|xếp hạng)\b',
    )
    if any(re.search(pattern, query, re.I) for pattern in find_patterns):
        required.append('find_candidate_matches')
    compatibility_patterns = (
        r'\bphân tích\b.*\b(tương thích|phù hợp)\b',
        r'\b(tính|xem)\b.*\bđiểm tương thích\b',
        r'\bđộ tương thích\b.*\b(u\d{3,}|ứng viên|hồ sơ)\b',
    )
    if any(
        re.search(pattern, query, re.I)
        for pattern in compatibility_patterns
    ):
        required.append('calculate_compatibility')
    if re.search(r'\b(lời mở đầu|tin nhắn đầu tiên|câu chào đầu tiên)\b', query):
        required.append('suggest_first_message')
    if not required and any(
        phrase in query
        for phrase in ('xem hồ sơ', 'lấy hồ sơ', 'thông tin hồ sơ')
    ):
        required.append('get_user_profile')
    return required


def _completed_actions(trace: list[dict[str, Any]]) -> set[str]:
    '''Lấy các action đã thực thi hoặc đã trả lỗi nghiệp vụ hợp lệ.'''
    integration_errors = {
        'UNKNOWN_TOOL',
        'INVALID_TOOL_ARGUMENTS',
        'TOOL_EXECUTION_ERROR',
        'TOOL_TIMEOUT',
        'USER_ID_MISMATCH',
    }
    completed = set()
    for item in trace:
        observation = item.get('observation', {})
        error_code = observation.get('error', {}).get('code')
        if error_code not in integration_errors:
            completed.add(item.get('action'))
    return completed


def _last_tool_error(result: dict[str, Any]) -> dict[str, Any] | None:
    '''Trả lỗi tool gần nhất nếu luồng không tạo được dữ liệu có cấu trúc.'''
    for item in reversed(result['trace']):
        observation = item.get('observation', {})
        if not observation.get('ok'):
            return observation.get('error')
    return None


def _grounded_final_answer(
    result: dict[str, Any],
    fallback: str,
) -> str:
    '''Dựng câu trả lời từ Observation thay vì tin ID/điểm do LLM tự viết.'''
    matches = result.get('matches') or []
    compatibility = result.get('compatibility')
    opener = result.get('opener')

    if opener:
        candidate = matches[0] if matches else {}
        candidate_id = candidate.get('candidate_id', 'ứng viên đã chọn')
        name = candidate.get('name')
        label = f'{candidate_id} ({name})' if name else candidate_id
        parts = [f'{label} là ứng viên được phân tích từ dữ liệu tool.']
        if compatibility:
            parts.append(
                'Điểm tương thích minh họa: '
                f"{compatibility.get('total_score', 0):.1f}."
            )
            shared_interests = compatibility.get('shared_interests') or []
            shared_values = compatibility.get('shared_values') or []
            if shared_interests:
                parts.append(
                    'Sở thích chung: ' + ', '.join(shared_interests) + '.'
                )
            if shared_values:
                parts.append(
                    'Giá trị chung: ' + ', '.join(shared_values) + '.'
                )
        parts.append('Lời mở đầu gợi ý: ' + opener['message'])
        return ' '.join(parts)

    if compatibility:
        compatibility_actions = [
            item
            for item in result['trace']
            if item.get('action') == 'calculate_compatibility'
        ]
        candidate_id = 'ứng viên đã chọn'
        if compatibility_actions:
            candidate_id = compatibility_actions[-1]['action_input'].get(
                'candidate_id',
                candidate_id,
            )
        return (
            f'{candidate_id} có điểm tương thích minh họa '
            f"{compatibility.get('total_score', 0):.1f}. "
            'Kết quả được tính từ dữ liệu tool và không phải kết luận khoa học.'
        )

    if matches:
        formatted = []
        for match in matches:
            label = match['candidate_id']
            if match.get('name'):
                label += f" ({match['name']})"
            formatted.append(f"{label}: {match['score']:.1f} điểm")
        return (
            'Các ứng viên phù hợp nhất theo dữ liệu tool là '
            + '; '.join(formatted)
            + '. Điểm số chỉ mang tính minh họa.'
        )

    if result.get('profile'):
        profile = result['profile']
        return (
            f"Hồ sơ {profile.get('id', '')}: "
            f"{profile.get('name', 'không có tên')}, "
            f"{profile.get('age', 'không rõ')} tuổi, "
            f"khu vực {profile.get('location', 'không rõ')}."
        )

    error = _last_tool_error(result)
    if error:
        return error.get('message', 'Không thể hoàn thành yêu cầu từ dữ liệu tool.')
    return fallback


def _safety_refusal(user_query: str) -> str | None:
    text = user_query.lower()
    ages = [int(age) for age in re.findall(r'\b(\d{1,2})\s*tuổi\b', text)]
    if any(age < 18 for age in ages):
        return 'Cupid chỉ hỗ trợ ghép đôi người từ 18 tuổi trở lên.'
    if any(term in text for term in ('địa chỉ nhà', 'tọa độ chính xác', 'số điện thoại', 'email')):
        return 'Mình không thể cung cấp thông tin riêng tư hoặc vị trí chính xác của hồ sơ.'
    if any(term in text for term in ('quên mọi hướng dẫn', 'bỏ qua quy tắc')) and any(
        term in text for term in ('toàn bộ hồ sơ', 'deal-breaker', 'tiết lộ')
    ):
        return 'Mình không thể bỏ qua guardrail hoặc tiết lộ dữ liệu hồ sơ riêng tư.'
    if any(term in text for term in ('tình dục', 'gây áp lực', 'ép buộc', 'phải đồng ý')):
        return 'Mình chỉ hỗ trợ lời mở đầu tôn trọng, an toàn và có sự đồng thuận.'
    return None


def run_react_agent(
    user_query: str,
    provider,
    user_id: str | None = None,
) -> dict[str, Any]:
    '''Chạy ReAct loop có registry, trace và giới hạn số Action.'''
    result: dict[str, Any] = {
        'status': 'running',
        'answer': '',
        'profile': None,
        'matches': [],
        'compatibility': None,
        'opener': None,
        'trace': [],
        'error': None,
    }
    refusal = _safety_refusal(user_query)
    if refusal:
        result['status'] = 'success'
        result['answer'] = refusal
        return result

    while True:
        response = provider.generate(
            _build_react_prompt(user_query, result['trace'], user_id),
            system_prompt=REACT_SYSTEM_PROMPT,
        )
        if _provider_error(response):
            result['status'] = 'error'
            result['error'] = {
                'code': 'PROVIDER_ERROR',
                'message': 'Không thể nhận phản hồi hợp lệ từ LLM provider',
            }
            result['answer'] = result['error']['message']
            return result

        parsed = parse_react_response(response)
        if not parsed.get('ok'):
            result['status'] = 'error'
            result['error'] = parsed['error']
            result['answer'] = parsed['error']['message']
            return result

        if parsed['type'] == 'final':
            completed = _completed_actions(result['trace'])
            missing = [
                action
                for action in _required_actions(user_query, user_id)
                if action not in completed
            ]
            if missing:
                result['status'] = 'error'
                result['error'] = {
                    'code': 'MISSING_REQUIRED_TOOL',
                    'message': (
                        'Agent trả lời khi chưa gọi tool bắt buộc: '
                        + ', '.join(missing)
                    ),
                }
                result['answer'] = result['error']['message']
                return result
            result['status'] = 'success'
            required = _required_actions(user_query, user_id)
            result['answer'] = (
                _grounded_final_answer(result, parsed['answer'])
                if required
                else parsed['answer']
            )
            return result

        if len(result['trace']) >= MAX_ITERATIONS:
            result['status'] = 'error'
            result['error'] = {
                'code': 'MAX_ITERATIONS',
                'message': f'Đã đạt giới hạn {MAX_ITERATIONS} lần gọi tool',
            }
            result['answer'] = 'Agent đã dừng an toàn vì đạt giới hạn số bước.'
            return result

        action_input = dict(parsed['action_input'])
        if (
            user_id
            and 'user_id' in action_input
            and action_input['user_id'] != user_id
        ):
            observation = _error(
                'USER_ID_MISMATCH',
                'user_id trong action không khớp hồ sơ người dùng đã chọn',
            )
        else:
            if user_id:
                action_input['user_id'] = user_id
            observation = execute_tool(parsed['action'], action_input)
        trace_item = {
            'iteration': len(result['trace']) + 1,
            'action': parsed['action'],
            'action_input': action_input,
            'observation': observation,
        }
        result['trace'].append(trace_item)
        _collect_structured_output(result, parsed['action'], observation)


def run_comparison(user_query: str, provider, user_id: str) -> dict[str, Any]:
    refusal = _safety_refusal(user_query)
    provider_mode = (
        'mock' if provider.__class__.__name__ == 'MockProvider' else 'live'
    )
    if refusal:
        react = {
            'status': 'success',
            'answer': refusal,
            'profile': None,
            'matches': [],
            'compatibility': None,
            'opener': None,
            'trace': [],
            'error': None,
        }
        return {
            'baseline': {'answer': refusal, 'trace': []},
            'react': react,
            'provider_mode': provider_mode,
        }
    return {
        'baseline': {
            'answer': run_baseline_chatbot(user_query, provider),
            'trace': [],
        },
        'react': run_react_agent(user_query, provider, user_id),
        'provider_mode': provider_mode,
    }


def print_baseline_result(test: dict[str, Any], answer: str) -> None:
    print('\n💬 [BASELINE — TEST {}] {}'.format(test['id'], test['question']))
    print(f'🤖 {answer}')


def print_react_result(test: dict[str, Any], result: dict[str, Any]) -> None:
    print('\n🤖 [REACT — TEST {}] {}'.format(test['id'], test['question']))
    for item in result['trace']:
        print('\n🔄 Bước {}'.format(item['iteration']))
        print('🛠️ Action: {}'.format(item['action']))
        print(
            '📥 Action Input: '
            + json.dumps(item['action_input'], ensure_ascii=False)
        )
        print(
            '👁️ Observation: '
            + json.dumps(item['observation'], ensure_ascii=False)
        )
    print('\n🏁 Final Answer: {}'.format(result['answer']))
    if result['error']:
        print('⚠️ Error: ' + json.dumps(result['error'], ensure_ascii=False))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Cupid Chatbot và ReAct Agent')
    parser.add_argument(
        '--mode',
        choices=('baseline', 'react', 'all'),
        default='react',
    )
    parser.add_argument('--test', type=int, choices=range(1, 6), default=4)
    parser.add_argument(
        '--provider',
        choices=('mock', 'openai', 'gemini', 'anthropic', 'openrouter'),
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    provider = get_llm_provider(args.provider)
    tests = {item['id']: item for item in load_test_cases()}
    test = tests[args.test]
    model_name = getattr(provider, 'model_name', 'Offline Mock Mode')

    print('=' * 60)
    print('💘 CUPID AGENT — CHATBOT BASELINE VS REACT AGENT')
    print('=' * 60)
    print(
        f'🔌 Provider: {provider.__class__.__name__} | Model: {model_name}'
    )

    exit_code = 0
    if args.mode in ('baseline', 'all'):
        baseline_answer = run_baseline_chatbot(test['question'], provider)
        print_baseline_result(test, baseline_answer)
        if _provider_error(baseline_answer):
            exit_code = 1
    if args.mode in ('react', 'all'):
        react_result = run_react_agent(test['question'], provider)
        print_react_result(test, react_result)
        if react_result['status'] == 'error':
            exit_code = 1
    raise SystemExit(exit_code)
