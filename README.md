# H.A.L.O.

H.A.L.O. is a local-first desktop AI companion. A Tauri + React shell supervises
two Python entry points: Brain owns chat, tools, permissions, memory, and durable
tasks; Voice is an authenticated sidecar reserved for the real-time audio path.
They communicate only over an authenticated loopback WebSocket whose port and
token are refreshed whenever Brain restarts.

Phases 0–2 are complete and Phase 3 is underway. The current Voice process is
audio-idle; browser automation, GUI control, and real speech are not yet shipped.
See [Halo-PRD.md](Halo-PRD.md), [phases.md](phases.md), and
[systemdesign/00-overview.md](systemdesign/00-overview.md) for product and
architecture details.

## Development

Requirements are Node.js, Rust/MSVC Build Tools, Python 3.11 or 3.12, and `uv`.

```powershell
uv sync --locked --extra full --python 3.12
cd ui; npm ci; cd ..
./dev.ps1
```

Use `./dev.ps1 -Browser` when a native Tauri window is unnecessary. Run the full
gate before submitting changes:

```powershell
./verify.ps1 -PythonCommand '.\.venv\Scripts\python.exe'
```

The root Python distribution provides `halo brain` and `halo voice`. `core`
installs omit document parsers and the local embedding runtime; `documents`,
`semantic`, and `full` add those capability groups. Official desktop builds
always select `full`. More setup detail is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Packaging and supply chain

`packaging/build-desktop.ps1` creates one full-profile Python backend executable
and an unsigned Tauri installer. Generated executables are not tracked. CI checks
the Python, npm, and Cargo locks, audits all three dependency graphs, and emits
CycloneDX inventories for code dependencies, the frozen backend, and the pinned
embedding-model asset. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Security and privacy

H.A.L.O. is designed for local execution and must never package API keys, session
files, databases, logs, caches, or model downloads. Please report vulnerabilities
using [SECURITY.md](SECURITY.md); do not open a public issue with exploit details.

## License status

The project owner has intentionally deferred choosing a project license until the
product is finished. No open-source license is currently granted, so public source
availability does not imply permission to copy, modify, or redistribute it. The
licenses of third-party dependencies and assets remain their respective owners'.
