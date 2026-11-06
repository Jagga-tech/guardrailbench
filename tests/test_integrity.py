import dataclasses
import json
import random

import pytest

from guardrailbench.case import Case, load_cases
from guardrailbench.cli import main
from guardrailbench.integrity import split_hash, scan_canaries

CHUNK = 1024 * 1024


def mk(i, text="hi"):
    return Case(id=f"c{i}", version=1, split="official", family=1, checkpoint="prompt",
                messages=[{"role": "user", "content": text}], target=0, label="benign",
                twin_id=None, twin_change=None, transform=None, source_pattern=None,
                canary=f"GRB-CANARY-{i:036d}", marker=None, deployment_card=None)


def write(path, cases, eol="\n"):
    path.write_bytes(eol.join(json.dumps(dataclasses.asdict(c), ensure_ascii=False) for c in cases).encode() + eol.encode())


def test_hash_stable_under_reordering(tmp_path):
    cs = [mk(i, "é") for i in range(5)]
    write(tmp_path / "a.jsonl", cs)
    shuffled = cs[:]
    random.Random(1).shuffle(shuffled)
    write(tmp_path / "b.jsonl", shuffled, eol="\r\n")
    assert split_hash(tmp_path / "a.jsonl") == split_hash(tmp_path / "b.jsonl")


def test_hash_changes_when_any_case_changes(tmp_path):
    cs = [mk(i) for i in range(3)]
    write(tmp_path / "a.jsonl", cs)
    cs[1].messages[0]["content"] = "changed"
    write(tmp_path / "b.jsonl", cs)
    assert split_hash(tmp_path / "a.jsonl") != split_hash(tmp_path / "b.jsonl")


def test_hash_refuses_broken_split(tmp_path):
    (tmp_path / "a.jsonl").write_text("not json\n")
    with pytest.raises(ValueError, match="a.jsonl:1"):
        split_hash(tmp_path / "a.jsonl")


def test_scan_finds_canary_split_across_read_chunks(tmp_path):
    c = "GRB-CANARY-" + "a" * 36
    for off in (CHUNK - 5, CHUNK - 1, CHUNK - len(c) + 1):
        f = tmp_path / f"d{off}.bin"
        f.write_bytes(b"x" * off + c.encode() + b"y" * 100)
        assert scan_canaries([f], {c}) == [(str(f), c)]


def test_scan_no_false_hits(tmp_path):
    c = "GRB-CANARY-" + "a" * 36
    f = tmp_path / "d.bin"
    f.write_bytes(b"x" * (CHUNK + 10) + c[:-1].encode() + b"zz")
    assert scan_canaries([f], {c}) == []


def test_scan_walks_dirs_once_per_file_and_skips_unreadable(tmp_path, capsys):
    c = "GRB-CANARY-" + "b" * 36
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "x.txt"
    f.write_text(c + c)
    assert scan_canaries([tmp_path, tmp_path / "missing"], {c}) == [(str(f), c)]
    assert "missing" in capsys.readouterr().err


def test_cli_hash_and_scan(tmp_path, capsys):
    write(tmp_path / "s.jsonl", [mk(1)])
    assert main(["hash", str(tmp_path / "s.jsonl")]) == 0
    assert capsys.readouterr().out.strip() == split_hash(tmp_path / "s.jsonl")
    d = tmp_path / "data"
    d.mkdir()
    (d / "clean.txt").write_text("nothing")
    assert main(["scan", "--cases", str(tmp_path / "s.jsonl"), str(d)]) == 0
    (d / "dirty.txt").write_text(mk(1).canary)
    assert main(["scan", "--cases", str(tmp_path / "s.jsonl"), str(d)]) == 1
    assert capsys.readouterr().out.strip() == f"{d / 'dirty.txt'}\t{mk(1).canary}"
