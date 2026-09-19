# Halo UI/UX: The Workspace

The expanded window — orb grows into a full glass app (user decision: **left sidebar** navigation). Panels defined in [systemdesign/10-ui](../systemdesign/10-ui.md); events it renders come from the [IPC contract](../systemdesign/11-ipc-contract.md).

## Layout
```
┌───────────────────────────────────────────────┐
│ ⊙ status strip: lane chip · mic · task chip   │  ← always visible
├──────┬────────────────────────────────────────┤
│ Chat │                                        │
│ Tasks│         main view                      │
│ Act. │         (Chat is default)              │
│ Mem. │                                        │
│Skills│                                        │
│ ⚙︎    │  [approval card overlays here]         │
└──────┴────────────────────────────────────────┘
```
- **Sidebar:** icon + label, active item marked by color + left indicator (never color alone). Order: Chat, Tasks, Activity, Memory, Skills, Settings (bottom, separated). Badges (amber count) on Tasks when approvals wait.
- **Status strip** (top): current **lane chip** (Fast / Takeover / Sandbox — always visible while a task runs, per PRD), mic state, and a compact running-task chip (name + progress + stop). Nothing else competes with it.
- Window: resizable, remembers size/position; `Esc` or the collapse button shrinks back into the orb (reverse of the summon animation).

## Navigation rules
- One primary view at a time; no drawers over drawers. Switching views preserves each view's scroll and state.
- Approval cards are **overlays anchored bottom-center of the main view**, never a new window — whatever view you're in, the card comes to you.
- Deep-jump affordances: clicking the orb's amber badge or a task chip lands directly on the relevant card/task.

## First-run onboarding (5 steps, ~2 min, skippable)
1. **Pick your hotkey** (default `Alt+Space`) — try it once.
2. **Model key** — OpenRouter key → stored in Windows Credential Manager, shown as ●●●.
3. **The 30-second trust tour** — three cards: what runs silently (Tier 1), what I tell you about (Tier 2), what I always ask first (Tier 3).
4. **Optional capabilities** — show Voice, browser, and integrations only when installed; unavailable capabilities explain what is planned and never request dead credentials or permissions.
5. **Ready check** — send a text message and show the connection/activity path working.

## Settings (single scrollable view, grouped)
- **General:** hotkey, theme (light/dark/auto), launch at startup.
- **Voice (when installed):** mic device, wake word on/off, narration on/off, voice-approval toggle (see [05-permissions-trust](05-permissions-trust.md)); otherwise one honest unavailable/install-later state.
- **Models:** current light/heavy IDs (editable, from [techstack/00](../techstack/00-stack-summary.md)) + this month's estimated spend.
- **Keys & connections:** OpenRouter today; capability-scoped speech, browser, and MCP credentials appear only when those capabilities exist — status dots + re-auth buttons.
- **Advanced (collapsed):** memory decay knobs, skill thresholds — the tunables from systemdesign, each with its default shown.
