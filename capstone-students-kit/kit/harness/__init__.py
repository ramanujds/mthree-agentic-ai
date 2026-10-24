"""Zero-cost teaching harness: everything here runs offline on a laptop CPU."""
from pathlib import Path
KIT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = KIT_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
