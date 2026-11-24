"""Makes the project root importable so tests work from any runner.

Locally pytest inserts the rootdir because tests live in their own folder, but on
CI the package paths (config, core, ui, utils) are not on sys.path unless we add
them explicitly.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
