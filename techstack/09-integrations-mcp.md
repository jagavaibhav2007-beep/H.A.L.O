# Tech Stack: API & MCP Integrations

Design: [systemdesign/09-integrations-mcp](../systemdesign/09-integrations-mcp.md). Global stack: [00-stack-summary](00-stack-summary.md).

Status: planned; no MCP client or integration runtime is active.

## Feature-specific
| Concern | Choice | Notes |
|---|---|---|
| MCP client | **official Python MCP SDK**, used directly | avoids a second adapter/orchestration layer; tools still enter through Halo's gate |
| Transport | stdio / local servers | run as subprocesses |
| Example servers | email (e.g. Gmail MCP), calendar, notes | user-authorized, per need |
| Direct APIs | `httpx` for REST when no MCP exists | Lane 1 |
| Credentials | **`keyring`** → Windows Credential Manager | no plaintext; redacted in logs |
| Gate | MCP/API tools pass through the same permission classifier | send/spend = Tier 3 |

## Cost note
- **Integration calls themselves are usually non-LLM** (direct API/MCP) → cheap/free beyond the provider's own terms.
- LLM cost is only the surrounding reasoning (light model by default).

## Preference order
API/MCP → browser automation → GUI automation. Cleanest channel first.
