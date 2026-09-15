"""Tests for the unified image-generation entry point."""

from __future__ import annotations

from types import SimpleNamespace

from pathlib import Path


def test_gpt_image_requests_base64_response():
    core = Path(__file__).resolve().parents[1] / "scripts" / "baoyu_image_gen_core.ts"
    source = core.read_text()

    assert 'model.startsWith("gpt-image")' in source
    assert 'body.response_format = "b64_json"' in source


def test_failed_backend_prints_codex_imagegen_fallback_hint(monkeypatch, capsys):
    import generate_image

    monkeypatch.setattr(generate_image, "build_command", lambda args: ("fake", ["fake"]))
    monkeypatch.setattr(
        generate_image, "get_codex_builtin_imagegen_fallback_enabled", lambda: True
    )
    monkeypatch.setattr(
        generate_image.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=17),
    )

    assert generate_image.main(["--image", "images/03.png"]) == 17
    error = capsys.readouterr().err
    assert "内置 ImageGen" in error
    assert "images/03.png" in error


def test_failed_backend_is_silent_when_codex_fallback_disabled(monkeypatch, capsys):
    import generate_image

    monkeypatch.setattr(generate_image, "build_command", lambda args: ("fake", ["fake"]))
    monkeypatch.setattr(
        generate_image, "get_codex_builtin_imagegen_fallback_enabled", lambda: False
    )
    monkeypatch.setattr(
        generate_image.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=17),
    )

    assert generate_image.main(["--image", "images/03.png"]) == 17
    assert capsys.readouterr().err == ""
