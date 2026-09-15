import base64
import pytest
import simple_gen

def test_image_request_and_output(monkeypatch, tmp_path):
    monkeypatch.setattr(simple_gen, '_load_backend', lambda: ('fake', 'https://example.com/v1', 'gpt-image-2'))
    raw=b'fake-image-bytes'
    def post(url, **kwargs):
        assert url == 'https://example.com/v1/images/generations'
        assert kwargs['timeout'] >= 300
        assert kwargs['json']['size'] == '1792x1024'
        assert kwargs['json']['model'] == 'gpt-image-2'
        class Response:
            status_code=200
            def json(self):
                return {'data': [{'b64_json': base64.b64encode(raw).decode()}]}
        return Response()
    monkeypatch.setattr(simple_gen.requests, 'post', post)
    output=tmp_path/'images'/'01.png'
    assert simple_gen.generate_image('test', str(output))
    assert output.read_bytes() == raw

def test_missing_backend_stops_before_request(monkeypatch):
    monkeypatch.setattr(simple_gen.config, 'load_env', lambda: None)
    for key in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_IMAGE_MODEL'):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit, match='缺少生图配置'):
        simple_gen._load_backend()
