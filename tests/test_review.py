"""The review server: who may post to it, and which pages its crops are cut from."""

import http.client
import json
import socket
import threading
from types import SimpleNamespace

import pytest

from roboscriptorium import cli, review
from roboscriptorium.disagreements import Verdicts


class _Recorder:
    html = "review.html"

    def __init__(self):
        self.recorded = []
        self.scan = None

    def state(self) -> dict:
        return {}

    def record(self, body: dict) -> dict:
        self.recorded.append(body)
        return {"ok": True}


@pytest.fixture
def server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    target = _Recorder()
    threading.Thread(target=review.serve, args=(target, port), daemon=True).start()
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            threading.Event().wait(0.02)
    return port, target


def _post(port: int, headers: dict) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps({"key": "k"})
    conn.putrequest("POST", "/api/verdict", skip_host=True)
    for k, v in {"Content-Length": str(len(body)), **headers}.items():
        conn.putheader(k, v)
    conn.endheaders(body.encode())
    status = conn.getresponse().status
    conn.close()
    return status


def test_a_post_from_anywhere_but_the_servers_own_page_is_refused(server):
    port, target = server
    own = f"127.0.0.1:{port}"
    refused = [
        {"Host": own},  # no JSON: what a plain form sends
        {"Host": own, "Content-Type": "text/plain"},
        {"Host": own, "Content-Type": "application/x-www-form-urlencoded"},
        {"Host": f"evil.example:{port}", "Content-Type": "application/json"},
        {"Host": "127.0.0.1:1", "Content-Type": "application/json"},
        {"Host": own, "Content-Type": "application/json", "Origin": "http://evil.example"},
        {"Host": own, "Content-Type": "application/json", "Origin": "null"},
    ]
    for headers in refused:
        assert _post(port, headers) == 403, headers
    assert target.recorded == []


def test_the_servers_own_page_may_post(server):
    port, target = server
    for host in (f"127.0.0.1:{port}", f"localhost:{port}"):
        json_type = {"Host": host, "Content-Type": "application/json; charset=utf-8"}
        assert _post(port, json_type) == 200
        assert _post(port, {**json_type, "Origin": f"http://{host}"}) == 200
    assert len(target.recorded) == 4


def test_golden_review_crops_from_the_pages_the_paragraphs_point_into(tmp_path, monkeypatch):
    layer = [SimpleNamespace(number=1, name="layer")]
    corrected = [SimpleNamespace(number=1, name="corrected")]
    stages = SimpleNamespace(pages=layer, corrected=corrected)
    book = SimpleNamespace(source=tmp_path / "source.pdf", stages=tmp_path, language="nl")
    seen = {}
    monkeypatch.setattr(cli, "_not_the_test_set", lambda *a: None)
    monkeypatch.setattr(cli, "_build_golden", lambda *a: (book, stages, "doc", [], ([], [])))
    monkeypatch.setattr(cli, "_verdicts", lambda b: Verdicts(tmp_path / "v.jsonl"))

    def find(doc, reference, pages, language, around=([], [])):
        seen["find"] = pages
        seen["language"] = language
        return []

    monkeypatch.setattr(cli.disagreements, "find", find)
    monkeypatch.setattr(review, "serve", lambda r, port: seen.setdefault("scan", r.scan.pages))
    cli.review_disagreements(tmp_path, None, None, True, 8765, False)
    # The paragraphs point into the pages before answers (`Line.source`), not the
    # corrected copy, where a typed line above would shift every crop.
    assert seen["find"] is layer
    assert seen["scan"][1] is layer[0]
    assert seen["language"] == "nl"
