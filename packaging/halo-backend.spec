"""Windows one-file backend; source packages only, never repository data."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules
from brain.capabilities import require_full

# A core-only environment must fail before emitting a misleading release.
require_full()
root = Path(SPECPATH).parent
datas, binaries, hiddenimports = [], [], []
for package in (
    "pypdf", "pypdfium2", "pypdfium2_raw", "mammoth", "openpyxl", "markdownify",
    "sqlite_vec", "fastembed", "keyring",
):
    package_data, package_bins, package_imports = collect_all(package)
    datas += package_data
    binaries += package_bins
    hiddenimports += package_imports
for package in ("brain", "voice", "halo", "langgraph.checkpoint.sqlite"):
    hiddenimports += collect_submodules(package)

a = Analysis(
    [str(root / "packaging" / "backend_entry.py")],
    pathex=[str(root), str(root / "brain"), str(root / "voice")],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], runtime_hooks=[], excludes=["tkinter", "pytest"],
    noarchive=False,
)
# Distribution metadata can contain installer-local URLs. They are unnecessary
# at runtime and must not expose a build checkout or credentials in the artifact.
a.datas = [
    item for item in a.datas
    if Path(item[0]).name not in ("direct_url.json", "INSTALLER", "RECORD")
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="halo-backend", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True,
)
