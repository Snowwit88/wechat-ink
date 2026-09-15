from types import SimpleNamespace
import pytest
import publish

@pytest.mark.parametrize('configured,expected', [('', ''), ('我的笔名', '我的笔名')])
def test_author_uses_only_configured_identity(monkeypatch, configured, expected):
    monkeypatch.setattr(publish, 'get_config', lambda: {'author': configured})
    args=SimpleNamespace(author=None, theme=None, sync_from_config=False)
    publish._resolve_config(args)
    assert args.author == expected

def test_explicit_author_is_preserved(monkeypatch):
    monkeypatch.setattr(publish, 'get_config', lambda: {'author': '配置署名'})
    args=SimpleNamespace(author='明确署名', theme=None, sync_from_config=False)
    publish._resolve_config(args)
    assert args.author == '明确署名'

def test_missing_config_does_not_invent_author(monkeypatch):
    def missing():
        raise publish.ConfigError('missing')
    monkeypatch.setattr(publish, 'get_config', missing)
    args=SimpleNamespace(author=None, theme=None, sync_from_config=False)
    publish._resolve_config(args)
    assert args.author == ''
