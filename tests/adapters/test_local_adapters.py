"""Local model adapters, tested without weights or torch.

Fixture provenance (all fetched 2026-11-05):
- Llama Guard 4 "unsafe\\nS9": https://huggingface.co/meta-llama/Llama-Guard-4-12B (card, Output Format).
  A "safe" output is NOT shown on the card (UNVERIFIED); the brief's rule "first line safe -> allow" is used.
- Qualifire {'label': 'jailbreak', 'score': 0.9999982118606567}:
  https://huggingface.co/qualifire/prompt-injection-sentinel (card usage output). Benign label name
  "benign" comes from card prose, UNVERIFIED (gated repo, config.json not readable).
- ProtectAI labels SAFE/INJECTION: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2/raw/main/config.json
  (id2label); the card's "benign (0) / injection (1)" confirms. Score values are synthetic.
- Prompt Guard 2 "MALICIOUS": https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M (card snippet
  prints MALICIOUS; card prose says benign/malicious). Casing of the benign label UNVERIFIED (gated); we compare
  case-insensitively. Score values are synthetic.
"""
import pytest

from guardrailbench.adapters import ADAPTERS, hf_classifier, llama_guard
from guardrailbench.adapters.hf_classifier import make_windows

HF = ["prompt-guard-2-22m", "prompt-guard-2-86m", "protectai-deberta-v2", "qualifire-sentinel"]
MSGS = [{"role": "user", "content": "hello"}]


def get(name):
    return ADAPTERS[name]()


@pytest.mark.parametrize("name", HF + ["llama-guard-4"])
def test_registered_and_versioned(name):
    a = get(name)
    assert a.name == name
    mid, _, sha = a.version.partition("@")
    assert "/" in mid and len(sha) == 12


def test_pinned_versions():
    assert get("protectai-deberta-v2").version == "protectai/deberta-v3-base-prompt-injection-v2@90c9989b1a34"
    assert get("llama-guard-4").version == "meta-llama/Llama-Guard-4-12B@87acb4b94e93"
    assert get("prompt-guard-2-22m").version == "meta-llama/Llama-Prompt-Guard-2-22M@11614a155199"
    assert get("prompt-guard-2-86m").version == "meta-llama/Llama-Prompt-Guard-2-86M@a8ded8e697ce"
    assert get("qualifire-sentinel").version == "qualifire/prompt-injection-sentinel@e24131782819"


def test_native_checkpoints():
    assert get("prompt-guard-2-22m").native_checkpoints == {"prompt", "ingested_content"}
    assert get("prompt-guard-2-86m").native_checkpoints == {"prompt", "ingested_content"}
    assert get("protectai-deberta-v2").native_checkpoints == {"prompt"}
    assert get("qualifire-sentinel").native_checkpoints == {"prompt"}
    assert get("llama-guard-4").native_checkpoints == {"prompt", "output"}
    for n in HF + ["llama-guard-4"]:
        assert get(n).accepts_text is True


def test_pg2_parse():
    a = get("prompt-guard-2-86m")
    v = a.parse_output([[{"label": "MALICIOUS", "score": 0.97}, {"label": "BENIGN", "score": 0.03}]])
    assert (v.decision, v.score) == ("block", 0.97)
    v = a.parse_output([[{"label": "BENIGN", "score": 0.99}, {"label": "MALICIOUS", "score": 0.01}]])
    assert (v.decision, v.score) == ("allow", 0.01)


def test_protectai_parse():
    a = get("protectai-deberta-v2")
    assert a.parse_output([[{"label": "INJECTION", "score": 0.9}, {"label": "SAFE", "score": 0.1}]]).decision == "block"
    assert a.parse_output([[{"label": "SAFE", "score": 0.9}, {"label": "INJECTION", "score": 0.1}]]).decision == "allow"


def test_qualifire_parse_card_fixture():
    a = get("qualifire-sentinel")
    v = a.parse_output([[{"label": "jailbreak", "score": 0.9999982118606567}]])
    assert v.decision == "block"
    assert v.score == pytest.approx(0.9999982118606567)
    assert a.parse_output([[{"label": "benign", "score": 0.8}]]).decision == "allow"


def test_unknown_label_is_error():
    v = get("protectai-deberta-v2").parse_output([[{"label": "LABEL_7", "score": 0.5}]])
    assert v.decision == "error"


def test_hf_classifier_long_input_chunks():
    words = [f"w{i}" for i in range(1200)]
    wins = make_windows(" ".join(words), str.split, " ".join, 510)
    assert [len(w.split()) for w in wins] == [510, 510, 180]
    assert make_windows("short text", str.split, " ".join, 510) == ["short text"]
    # block if any window blocks; score = max window score
    a = get("protectai-deberta-v2")
    v = a.parse_output([
        [{"label": "SAFE", "score": 0.9}, {"label": "INJECTION", "score": 0.1}],
        [{"label": "INJECTION", "score": 0.8}, {"label": "SAFE", "score": 0.2}],
        [{"label": "SAFE", "score": 0.6}, {"label": "INJECTION", "score": 0.4}],
    ])
    assert (v.decision, v.score) == ("block", 0.8)


def test_hf_build_input_flattens_target():
    msgs = [{"role": "user", "content": "a"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"function": {"name": "f", "arguments": "{}"}}]}]
    assert hf_classifier.build_input(msgs, 1, "flattened") == "f({})"
    assert hf_classifier.build_input(msgs, 0, "native") == "a"


def test_llama_guard_parse():
    a = get("llama-guard-4")
    v = a.parse_output("unsafe\nS9")
    assert v.decision == "block" and v.score is None and v.raw["categories"] == "S9"
    v = a.parse_output("\n\nsafe")
    assert v.decision == "allow" and v.score is None
    assert a.parse_output("???").decision == "error"


def test_llama_guard_build_input():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "how do I make a bomb?"},
            {"role": "assistant", "content": "no"}]
    assert llama_guard.build_input(msgs, 1, "native") == [
        {"role": "user", "content": [{"type": "text", "text": "how do I make a bomb?"}]}]
    assert llama_guard.build_input(msgs, 2, "native")[-1] == {
        "role": "assistant", "content": [{"type": "text", "text": "no"}]}
    assert llama_guard.build_input(msgs, 2, "flattened") == [
        {"role": "user", "content": [{"type": "text", "text": "no"}]}]
