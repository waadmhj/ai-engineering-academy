"""The tutor reveal: when every workshop passes (here: using the reference solutions), the tutor runs on that code."""
import shutil

from app.config import get_settings


def test_full_forge_reveal(client, tmp_path, monkeypatch):
    real = get_settings().forge_dir
    fake = tmp_path / "forge"
    shutil.copytree(real / "tests", fake / "tests")
    shutil.copytree(real / "solutions", fake / "workspace")  # pretend the learner implemented everything
    shutil.copytree(real / "solutions", fake / "solutions")
    shutil.copy(real / "runner.py", fake / "runner.py")
    monkeypatch.setattr(get_settings(), "forge_dir", fake)
    monkeypatch.setenv("TUTOR_PROVIDER", "none")

    for i in range(1, 8):
        r = client.post(f"/api/forge/forge-{i}/verify").json()
        assert r["passed"], r["output"]
    st = client.get("/api/tutor/status").json()
    assert st["revealed"] and st["assembled"] == 7 and all(p["capability"] for p in st["parts"])

    ans = client.post("/api/tutor/ask", json={"question": "Why are attention scores divided by the square root of d_k?"}).json()
    assert ans["ok"], ans
    assert ans["used_llm"] is False and ans["answer"]
    assert any(s["doc_id"] == "sm-05" for s in ans["sources"])
