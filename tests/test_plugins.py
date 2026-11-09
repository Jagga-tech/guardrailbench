import os
import subprocess
import sys


def test_plugin_module_registers(tmp_path):
    (tmp_path / "my_private_adapter.py").write_text(
        "from guardrailbench.adapters import register\n"
        "register('my-private')(lambda: None)\n")
    env = {**os.environ, "GUARDRAILBENCH_PLUGINS": " my_private_adapter ,",
           "PYTHONPATH": os.pathsep.join([str(tmp_path), os.environ.get("PYTHONPATH", "")])}
    out = subprocess.run([sys.executable, "-c",
                          "from guardrailbench.adapters import ADAPTERS; print('my-private' in ADAPTERS)"],
                         env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "True"
