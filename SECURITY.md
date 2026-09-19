# Security policy

## Reporting

Report suspected vulnerabilities privately through the repository's GitHub
Security tab using a private vulnerability report. Include affected versions,
reproduction steps, impact, and any suggested mitigation. Do not include real API
keys, user databases, or session tokens and do not open a public issue with an
unfixed exploit.

## Scope

Security scope includes authentication or permission bypass, unintended file or
command access, credential/session disclosure, sidecar escape or orphaning, remote
content fetched by local document parsing, and resource-exhaustion conditions from
a user-opened document that can hang or terminate the resident application.
Third-party service availability, unsupported platforms, and attacks requiring a
previously compromised operating-system account are normally outside scope unless
they cross a H.A.L.O. trust boundary.

Only the current `main` branch is supported. There is no published production
release or security-response SLA yet. Reports will be acknowledged and assessed
before details are disclosed publicly.
