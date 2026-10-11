"""CreditMera Experiments Package."""
import sys
from pathlib import Path

_backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))
