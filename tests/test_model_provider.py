import json

from roadsaarthi import config
from roadsaarthi import model_provider


def test_request_contract_and_localhost_only(monkeypatch):
    seen = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"response": '{"category":"Pothole","summary":"A pothole."}', "model":"fake"}).encode()
    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return Response()
    monkeypatch.setattr(model_provider, "urlopen", fake_urlopen)
    result = model_provider.call_model("A pothole", "English", "category_and_summary")
    req = seen["request"]
    body = json.loads(req.data)
    assert req.full_url == "http://127.0.0.1:11434/api/generate"
    assert seen["timeout"] == config.ASSISTANCE_TIMEOUT_SECONDS
    assert body["think"] is False and body["keep_alive"] == 0
    assert len(body["prompt"]) < 1200
    assert result["category"] == "Pothole"


def test_input_is_capped(monkeypatch):
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"response":"{}"}'
    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        return Response()
    monkeypatch.setattr(model_provider, "urlopen", fake_urlopen)
    model_provider.call_model("x" * (config.ASSISTANCE_INPUT_LIMIT + 50), "English", "summary")
    assert len(captured["body"]["prompt"]) < config.ASSISTANCE_INPUT_LIMIT + 500
