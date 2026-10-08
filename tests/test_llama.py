import json
import struct

import httpx
import numpy as np

from roboscriptorium.clients import decide, llama


def _readout(tmp_path, monkeypatch, rows: np.ndarray) -> None:
    header = json.dumps(
        {"weight": {"dtype": "F32", "shape": list(rows.shape), "data_offsets": [0, rows.nbytes]}}
    ).encode()
    (tmp_path / "4b-decision_readout.safetensors").write_bytes(
        struct.pack("<Q", len(header)) + header + rows.astype(np.float32).tobytes()
    )
    (tmp_path / "4b-calibration.json").write_text(json.dumps({"fit": {"temperature": 2.0}}))
    monkeypatch.setattr(llama, "READOUTS", tmp_path)


def test_the_question_is_laid_out_as_imajev_was_trained_with_unknown_last():
    question = decide.choice("Which text?", {"a": "exactly ⟨Iemand⟩", "b": "exactly ⟨lemand⟩"})
    rendered, values = llama.prompt({"line": 3, "page": 9}, question, "<IMG>")
    assert values == ["a", "b", "unknown"]
    assert rendered.startswith("<|im_start|>user\n<IMG>Inspect the available evidence")
    assert 'State: {"line": 3, "page": 9}\nQuestion: Which text?\n' in rendered
    assert "A: a — exactly ⟨Iemand⟩\nB: b — exactly ⟨lemand⟩\nC: unknown — " in rendered
    assert rendered.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")


def test_the_answer_is_the_readout_on_the_last_hidden_state(tmp_path, monkeypatch):
    # Three codes over a two-wide hidden state: B's row points where the state does.
    _readout(tmp_path, monkeypatch, np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]))
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/props":
            return httpx.Response(200, json={"media_marker": "<M>"})
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=[{"embedding": [[9.0, 9.0], [0.0, 4.0]]}])

    http = httpx.Client(base_url="http://llama", transport=httpx.MockTransport(handler))
    client = llama.ReadoutClient("imajev-4b", "http://llama", client=http)
    question = decide.choice("Which?", {"a": "x", "b": "y"})
    answer = client.decide({}, {"reading": question}, image_png=b"png")["reading"]
    assert answer.value == "b"
    # Logits 0, 4/2, 0 after the temperature.
    expect = np.exp([0.0, 2.0, 0.0]) / np.exp([0.0, 2.0, 0.0]).sum()
    assert abs(answer.probabilities["b"] - expect[1]) < 1e-6
    (body,) = sent[0]["content"]
    assert body["prompt_string"].startswith("<|im_start|>user\n<M>")
    assert body["multimodal_data"] == ["cG5n"]
