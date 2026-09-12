"""The Claude hook is advisory even when its interpreter/config cannot be used."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / 'hooks/scripts/check-setup.sh'


@pytest.mark.parametrize('code', [0, 2])
def test_hook_handles_setup_failure_and_spaced_plugin_path(tmp_path, code):
    bash = shutil.which('bash')
    if not bash or os.name == 'nt':
        pytest.skip('Bash fixture runs on POSIX; Windows runtime checks are separate')
    plugin = tmp_path / 'plugin with spaces'
    script = plugin / 'skills/watch/scripts/setup.py'
    script.parent.mkdir(parents=True)
    script.write_text(f'raise SystemExit({code})\n')
    result = subprocess.run([bash, str(HOOK)], env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(plugin)}, capture_output=True, text=True)
    assert result.returncode == 0
    assert bool(result.stdout) == bool(code)


def test_hook_handles_broken_interpreters(tmp_path):
    bash = shutil.which('bash')
    if not bash or os.name == 'nt':
        pytest.skip('Requires POSIX executable scripts')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    for name in ('python', 'python3'):
        path = bindir / name
        path.write_text('#!/bin/sh\nexit 1\n')
        path.chmod(0o755)
    result = subprocess.run([bash, str(HOOK)], env={**os.environ, 'PATH': str(bindir), 'CLAUDE_PLUGIN_ROOT': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode == 0 and 'Python' in result.stdout
