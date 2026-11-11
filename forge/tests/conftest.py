"""Put the learner's workspace (or another dir via FORGE_DIR) first on sys.path."""
import os
import sys
from pathlib import Path

FORGE_DIR = Path(os.environ.get("FORGE_DIR", Path(__file__).resolve().parents[1] / "workspace")).resolve()
sys.path.insert(0, str(FORGE_DIR))
