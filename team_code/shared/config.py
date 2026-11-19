# EXTRACT for the public copy. This is not the team's whole file.
# Source: the team's `shared/config.py` at commit c7a2c32 (the team's repository is private).
# SHA-256 of the source file: 23828c939f37653bc0c1bf1bb8f0dd6f021ec116b93d61a429397b2d70745bf1
# Kept: only the parts the Long Island run uses (in some files, nothing), copied line for line. Left out:
# everything else, because the team's full files describe the restricted San Francisco Bay sensor data. Text
# marked "[Public copy: ...]" was changed or added by this project. See team_code/README.md.

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


MODEL3_HAB_DIR = PROJECT_ROOT / "model3" / "data" / "raw" / "model3_hab"


MODEL3_HAB_CODE_DIR = MODEL3_HAB_DIR / "code"
