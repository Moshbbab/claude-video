"""Gemini adapter: payloads, parsing, and failures against a fake urlopen. No network."""
from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

import gemini

KEY = 'unit-test-key-DO-NOT-LEAK'


class FakeResponse:
    def __init__(self, body=b'{}', status=200, headers=None):
        self.status, self.headers, self._body = status, headers or {}, body
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False


def http_error(code, body):
    return HTTPError('https://example.invalid', code, 'error', {}, io.BytesIO(body))


def answer(*texts):
    steps = [{'type': 'processing_call', 'id': 'c1'}, {'type': 'processing_result', 'call_id': 'c1'}, {'type': 'thought'}]
    steps.append({'type': 'model_output', 'content': [{'type': 'text', 'text': t} for t in texts]})
    return json.dumps({'status': 'completed', 'steps': steps, 'usage': {'total_tokens': 4348}}).encode()


@pytest.fixture
def calls(monkeypatch):
    """Record every request; replies are popped from calls.replies in order."""
    class Calls(list):
        replies = []
    recorded = Calls()
    def fake(request, timeout=None):
        recorded.append(request)
        reply = recorded.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(gemini, 'urlopen', fake)
    return recorded


@pytest.mark.parametrize('source,expected', [
    ('https://www.youtube.com/watch?v=rlOpbu3Enkw', True),
    ('https://youtu.be/rlOpbu3Enkw', True),
    ('https://m.youtube.com/shorts/abc123', True),
    ('https://www.youtube.com/playlist?list=PL1', False),
    ('https://vimeo.com/123', False),
    ('/tmp/clip.mp4', False),
    ('https://notyoutube.com/watch?v=x', False),
])
def test_is_youtube(source, expected):
    assert gemini.is_youtube(source) is expected


def test_prompt_always_demands_timestamps():
    assert 'What is on the whiteboard?' in gemini.build_prompt('What is on the whiteboard?')
    assert 'MM:SS' in gemini.build_prompt('What is on the whiteboard?')
    default = gemini.build_prompt(None)
    assert 'summary' in default.lower() and 'MM:SS' in default


def test_agentic_youtube_payload_and_header_only_key(calls):
    calls.replies = [FakeResponse(answer('At 00:10 the screen turns blue.'))]
    result = gemini.ask({'uri': 'https://youtu.be/abc'}, 'When does it change?', model='gemini-3.7-flash', key=KEY)
    request = calls[0]
    assert request.full_url == 'https://generativelanguage.googleapis.com/v1beta/interactions'
    assert KEY not in request.full_url
    assert request.get_header('X-goog-api-key') == KEY
    payload = json.loads(request.data)
    assert payload['model'] == 'gemini-3.7-flash'
    assert payload['input'][0] == {'type': 'video', 'uri': 'https://youtu.be/abc', 'processing': 'agentic'}
    assert payload['input'][1]['type'] == 'text' and 'When does it change?' in payload['input'][1]['text']
    assert result == {'text': 'At 00:10 the screen turns blue.', 'model': 'gemini-3.7-flash',
                      'processing': 'agentic', 'total_tokens': 4348}


def test_clip_uses_static_processing_with_duration_strings(calls):
    calls.replies = [FakeResponse(answer('Blue.'))]
    result = gemini.ask({'uri': 'https://generativelanguage.googleapis.com/v1beta/files/x', 'mime_type': 'video/mp4'},
                        None, model='m', key=KEY, clip=(1200.4, 1500.2))
    video = json.loads(calls[0].data)['input'][0]
    assert video['mime_type'] == 'video/mp4'
    assert video['processing'] == {'type': 'static', 'start_offset': '1200s', 'end_offset': '1501s'}
    assert result['processing'] == 'static clip 20:00–25:01'


def test_open_ended_clip_omits_the_missing_bound(calls):
    calls.replies = [FakeResponse(answer('ok'))]
    gemini.ask({'uri': 'https://youtu.be/abc'}, None, model='m', key=KEY, clip=(90.0, None))
    assert json.loads(calls[0].data)['input'][0]['processing'] == {'type': 'static', 'start_offset': '90s'}


def test_multiple_text_parts_are_joined(calls):
    calls.replies = [FakeResponse(answer('First.', 'Second.'))]
    assert gemini.ask({'uri': 'https://youtu.be/abc'}, None, model='m', key=KEY)['text'] == 'First.\nSecond.'


def test_empty_answer_is_a_failure(calls):
    calls.replies = [FakeResponse(json.dumps({'steps': [{'type': 'thought'}]}).encode())]
    with pytest.raises(SystemExit, match='Gemini response'):
        gemini.ask({'uri': 'https://youtu.be/abc'}, None, model='m', key=KEY)


@pytest.mark.parametrize('reply,category', [
    (http_error(401, b'[{"error":{"code":401,"message":"Request had invalid authentication credentials.","status":"UNAUTHENTICATED"}}]'), 'auth'),
    (http_error(403, b'{"error":{"message":"API key not valid","code":"permission_denied"}}'), 'auth'),
    (http_error(429, b'{"error":{"message":"Quota exceeded","code":"resource_exhausted"}}'), 'quota'),
    (http_error(400, b'{"error":{"message":"Invalid input at \'input[0].processing\'.","code":"invalid_request"}}'), 'rejected'),
    (http_error(503, b'upstream unavailable'), 'service'),
    (URLError('certificate verify failed'), 'network'),
    (TimeoutError('timed out'), 'network'),
    (FakeResponse(b'<html>not json</html>'), 'response'),
])
def test_failures_are_categorized_and_never_leak_the_key(calls, reply, category):
    calls.replies = [reply]
    with pytest.raises(SystemExit) as caught:
        gemini.ask({'uri': 'https://youtu.be/abc'}, None, model='m', key=KEY)
    message = str(caught.value)
    assert message.startswith(f'Gemini {category}:')
    assert KEY not in message
    assert '--engine local' in message


def test_key_echoed_by_the_server_is_redacted(calls):
    calls.replies = [http_error(400, json.dumps({'error': {'message': f'bad key {KEY}'}}).encode())]
    with pytest.raises(SystemExit) as caught:
        gemini.ask({'uri': 'https://youtu.be/abc'}, None, model='m', key=KEY)
    assert KEY not in str(caught.value) and '[redacted]' in str(caught.value)
