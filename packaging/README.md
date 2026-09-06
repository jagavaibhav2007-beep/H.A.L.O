# Windows desktop packaging

From the repository root, after `npm ci` in `ui`:

```powershell
./packaging/build-desktop.ps1
```

This selects the locked **full** Python profile and pinned build-only PyInstaller
group, freezes one console-subsystem backend (hidden by Tauri), and builds an
unsigned Windows x64 NSIS installer. The ordinary source configuration disables
bundling; `tauri.release.conf.json` enables it and declares the target-suffixed
`externalBin`. Running a bare source build is not an installer release route.
The desktop workflow is manual and produces artifacts, not a published release.

The installed layout places `halo-backend.exe` beside the desktop executable.
Tauri starts it twice, with `brain` and `voice` modes. Release supervision never
searches for Python or the source checkout. Each generation starts suspended,
joins lifetime and generation Job Objects, then resumes; a crashed one-file
launcher cannot leave an interpreter holding the Brain session lock.
Debug builds retain source development; `HALO_USE_BUNDLED_BACKEND=1` explicitly
selects an adjacent bundle for native debugging.

PDF workers reuse the executable through an early internal mode. An external
command helper resets the frozen DLL search path only in its own process, so
concurrent Brain imports are unaffected. It preserves the bootloader's existing
reserved environment while starting, then strips it before executing the
approved external command. The permission gate, structured argv, identity
recheck, output limits, and task Job Object still own command execution.
Python scripts and external coding CLIs require their respective external
interpreters/tools; bundling Brain and Voice does not bundle those applications.

Verify the actual artifact:

```powershell
./.venv/Scripts/python.exe shared/python_profile_check.py --executable dist/halo-backend.exe --profile full
```

The check copies it to an unrelated Unicode/space path, removes Python from PATH,
uses temporary local data, tests native PDF workers/cancellation and command
output, and exercises Brain authentication plus Voice reconnect after restart.
Dependency imports check PDFium, ONNX and keyring collection, not a downloaded
embedding model or successful use of the host's credential store.

No user database, secrets, cache, logs or repository tree is an input to the
freeze. Installer-local `direct_url.json` metadata is excluded. Generated binaries
are ignored by Git. Source paths in transient build logs are not release assets.

Still required before distribution: signing/notarization policy (Windows signing
here), antivirus/SmartScreen evaluation, clean-machine install/upgrade/uninstall,
WebView2 and VC-runtime prerequisite checks, native window and credential-store
checks. None is implied by a successful local backend test. Project license
selection remains deferred by the user.

Build references: [Tauri sidecars](https://v2.tauri.app/develop/sidecar/) and
[PyInstaller multiprocessing and DLL search](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).
