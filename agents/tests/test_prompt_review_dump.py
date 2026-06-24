from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prompt_review_dump", ROOT / "scripts" / "prompt_review_dump.py"
)
prompt_review_dump = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prompt_review_dump)


def test_prompt_review_dump_writes_human_review_artifacts(tmp_path):
    out_root = tmp_path / "prompt-review"
    code = prompt_review_dump.main(
        [
            "--run-id",
            "test-run",
            "--out-dir",
            str(out_root),
        ]
    )

    assert code == 0
    out_dir = out_root / "test-run"
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["userId"] == "u_sakura"
    assert manifest["bookCount"] == 4

    review = (out_dir / "review.md").read_text(encoding="utf-8")
    assert "# Prompt Review" in review
    assert "STEP1 Reader Profile" in review
    assert "STEP3-5 Book Outlets" in review

    raw = out_dir / "raw"
    assert (raw / "01_reader_profile.json").exists()
    assert (raw / "02_plan_set_verdict.json").exists()
    assert len(list(raw.glob("03_author_casting_*.json"))) == 4
    assert len(list(raw.glob("04_book_draft_*.json"))) == 4
    assert len(list(raw.glob("05_shelved_book_*.json"))) == 4
