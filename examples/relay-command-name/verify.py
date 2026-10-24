"""Check compiled XAML and real headless pointer input, plus failure controls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DOTNET = os.environ.get("DOTNET", "dotnet")

def build(root):
    subprocess.run([DOTNET, "restore", "--locked-mode"], cwd=root, check=True, capture_output=True, text=True)
    return subprocess.run([DOTNET, "build", "-c", "Release", "--no-restore"], cwd=root, capture_output=True, text=True)

def run(root):
    proc = subprocess.run([DOTNET, str(root / "bin/Release/net10.0/RelayCommandName.dll")], cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert not proc.stderr.strip(), proc.stderr
    return json.loads(proc.stdout)

def verify(report):
    expected = []
    for calls, controls, click_events, control_events in [(0,0,0,0), (1,0,1,0), (2,0,2,0), (0,0,2,0), (1,0,3,0), (1,1,3,1)]:
        expected.append({"Calls":calls, "Text":str(calls), "ControlCalls":controls,
                         "ControlText":str(controls), "MainClickEvents":click_events,
                         "ControlClickEvents":control_events})
    assert report["Snapshots"] == expected, report["Snapshots"]
    assert report["OriginalCalls"] == 2 and report["OriginalControlCalls"] == 0, report

result = build(ROOT)
assert result.returncode == 0, result.stdout + result.stderr
verify(run(ROOT))
print("PASS compiled binding, two real pointer clicks, displayed counts, new DataContext and non-On control")

with tempfile.TemporaryDirectory(prefix="relay-command-check-") as directory:
    parent = Path(directory)
    def variant(name, old, new, filename="TestWindow.axaml"):
        path = parent / name
        shutil.copytree(ROOT, path, ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))
        xaml = path / filename
        text = xaml.read_text()
        assert old in text
        xaml.write_text(text.replace(old, new))
        return path

    wrong = variant("wrong-name", "{Binding PointerPressedCommand}", "{Binding OnPointerPressedCommand}")
    result = build(wrong)
    assert result.returncode != 0, result
    assert "AVLN2000" in result.stdout + result.stderr, result
    assert "Unable to resolve property or method of name 'OnPointerPressedCommand'" in result.stdout + result.stderr, result
    print("PASS original OnPointerPressedCommand binding fails XAML compilation")

    missing = variant("missing-command", ' Command="{Binding PointerPressedCommand}"', "")
    result = build(missing)
    assert result.returncode == 0, result.stdout + result.stderr
    report = run(missing)
    assert report["Snapshots"][2]["MainClickEvents"] == 2, report
    try:
        verify(report)
    except AssertionError:
        pass
    else:
        raise AssertionError("Removing the command binding must fail the final UI checks")
    print("PASS clicking an unbound Button is rejected by the result checks")

    no_input = variant("missing-pointer", "window.MouseDown(point, MouseButton.Left);", "// No pointer press is sent.", "Program.cs")
    result = build(no_input)
    assert result.returncode == 0, result.stdout + result.stderr
    report = run(no_input)
    try:
        verify(report)
    except AssertionError:
        pass
    else:
        raise AssertionError("Missing pointer input must fail the final UI checks")
    print("PASS omitting pointer presses is rejected by the result checks")
