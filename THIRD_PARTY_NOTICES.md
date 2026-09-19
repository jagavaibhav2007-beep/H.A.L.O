# Third-party notices and release inventory

H.A.L.O. depends on separately licensed Python, npm, Cargo, native, and model
components. This file is a release checklist, not a substitute for their license
texts and not a license for H.A.L.O.

Before distributing a build, generate the release inventories:

```powershell
./scripts/generate-sbom.ps1 -BackendPath ./dist/halo-backend.exe
```

The command emits reproducible CycloneDX JSON inventories for the locked Python,
npm, and Cargo graphs plus bundled/model assets. CI uploads these alongside the
unsigned build. Missing/unknown machine-readable license fields are reported as
unknown and require human review; they are never treated as permissive.

Release review must separately cover:

- PDFium binaries included through `pypdfium2` and their notices;
- ONNX Runtime, sqlite-vec, keyring backends, WebView2, and Microsoft VC runtime
  redistribution requirements;
- icon, font, and other visual asset provenance;
- `Qdrant/bge-small-en-v1.5-onnx-Q` at the pinned revision and checksum documented
  in `techstack/model-assets.md`; repository metadata declares Apache-2.0 while
  the FastEmbed registry labels the model MIT, so redistribution terms must be
  resolved before model weights are shipped;
- all components whose generated SBOM license field is absent or unknown.

Model weights and user model caches are not bundled by the current installer.
The project license remains deliberately undecided and no SPDX project-license
field should be added until the owner makes that choice.
