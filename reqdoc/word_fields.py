"""Fill in a Word document's table of contents (and page numbers) by letting Microsoft Word do it.

python-docx cannot lay out pages, so it cannot know which page a heading lands on. If Word is installed
(it is on the team's PCs) we open the finished file in a hidden Word, update the fields and save it, so the
contents page is already complete when a person opens the file. When Word is missing or anything goes
wrong this returns None and the caller falls back to "Word asks to update fields when the file opens".
"""
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

TIMEOUT_SECONDS = 90
_lock = threading.Lock()  # one Word job at a time

# ASCII only: Windows PowerShell 5.1 misreads UTF-8 without a BOM.
_SCRIPT = r"""
param([string]$Path)
$ErrorActionPreference = 'Stop'
$wasRunning = [bool](Get-Process WINWORD -ErrorAction SilentlyContinue)
$m = [Type]::Missing
$w = New-Object -ComObject Word.Application
try {
  if (-not $wasRunning) { $w.Visible = $false; $w.DisplayAlerts = 0 }
  $d = $w.Documents.Open($Path, $false, $false, $false, $m, $m, $false, $m, $m, $m, $m, $false)
  try {
    foreach ($t in $d.TablesOfContents) { $t.Update() }
    $d.Fields.Update() | Out-Null
    $d.Save()
  } finally { $d.Close(0) }
} finally {
  if (-not $wasRunning) { $w.Quit() }   # never close a Word the person already had open
}
"""


def refresh_fields(docx: bytes) -> bytes | None:
    """The same document with its table of contents filled in, or None if Word could not do it."""
    if sys.platform != "win32":
        return None
    with _lock, tempfile.TemporaryDirectory(prefix="reqdoc_word_") as tmp:
        folder = Path(tmp)
        doc, script = folder / "doc.docx", folder / "refresh.ps1"
        doc.write_bytes(docx)
        script.write_text(_SCRIPT, encoding="ascii")
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), str(doc)],
                capture_output=True, timeout=TIMEOUT_SECONDS, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return None
        out = doc.read_bytes()
        # a failed run leaves our own file untouched (same bytes): treat that as "no refresh"
        return out if result.returncode == 0 and out != docx else None
