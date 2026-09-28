import json
import subprocess
import sys


def test_cli_exports_and_regression_gate(tmp_path):
    out=tmp_path/'evidence'
    command=[sys.executable,'-m','app.cli','demo','--db',str(tmp_path/'cli.sqlite3'),'--out',str(out),'--fail-on-regression']
    proc=subprocess.run(command,capture_output=True,text=True)
    assert proc.returncode==1,proc.stderr
    data=json.loads((out/'comparison.json').read_text())
    assert data['counts']=={'improved':8,'regressed':5,'unchanged':37}
    assert 'Synthetic fixtures' in (out/'comparison.md').read_text()
    assert (out/'baseline-run.json').is_file()
    assert (out/'candidate-run.json').is_file()


def test_cli_rejects_incomplete_comparison():
    proc=subprocess.run([sys.executable,'-m','app.cli','compare'],capture_output=True,text=True)
    assert proc.returncode==2
