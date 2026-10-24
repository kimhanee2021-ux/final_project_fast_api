import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import app.main
assert 'keras' not in sys.modules, 'keras가 import 시점에 불려옴'
assert 'torch' not in sys.modules, 'torch가 import 시점에 불려옴'
print('ok')
"""


def test_importing_the_app_needs_no_env_and_loads_no_ml_framework():
    # 설정을 모두 비운 새 프로세스에서 import 만으로는 아무것도 읽거나 만들지 않아야 한다
    env = {k: v for k, v in os.environ.items() if k.upper() != "MODEL_DIR"}
    result = subprocess.run(
        [sys.executable, "-I", "-c", SCRIPT], capture_output=True, text=True, env=env, cwd=ROOT
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
