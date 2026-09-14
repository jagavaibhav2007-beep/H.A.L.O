import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { useHaloStore } from "../state/store";
import { SettingsView } from "./SettingsView";

beforeEach(() => {
  installLocalStorage();
  useHaloStore.setState(useHaloStore.getInitialState(), true);
});
afterEach(cleanup);

function installLocalStorage() {
  const values = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, String(value)),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    },
  });
}

test("shows an unknown key state and never claims mock model IDs", () => {
  const view = render(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByRole("status").textContent).toContain("checking stored status…");
  expect(view.container.textContent).not.toContain("halo-mock");
  expect(screen.getByText("Selected automatically by the Brain")).not.toBeNull();
  useHaloStore.setState({ settings: { openrouter_key: "missing" } });
  view.rerender(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByRole("status").textContent).toContain("not set");
});

test("an unavailable Brain disables key controls without an endless status spinner", () => {
  useHaloStore.getState().applyConnectionEvent({ type: "ws_unavailable" });
  render(<SettingsView sendSettingsUpdate={vi.fn()} />);

  expect(screen.getByRole("status").textContent).toContain("unavailable until Halo is running");
  expect((screen.getByLabelText("OpenRouter") as HTMLInputElement).disabled).toBe(true);
  expect(screen.getByText("Voice input is not available in this build; typed chat still works.")).toBeTruthy();
  expect(document.querySelector(".halo-spinner")).toBeNull();
});

test("settings groups continue the view heading hierarchy", () => {
  render(<SettingsView sendSettingsUpdate={vi.fn()} />);

  expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
    "General",
    "Voice",
    "Models",
    "Accessible folders",
    "Keys & connections",
  ]);
});

test("runtime diagnostics distinguish unknown, lexical and ready semantic retrieval", () => {
  const view = render(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByText("Not reported by this Brain")).toBeTruthy();
  useHaloStore.getState().applyFrame({
    type: "capabilities_state", id: "caps", ts: "2026-09-06T00:00:00Z",
    voice_input: false, task_controls: true, skill_controls: false, demo_scenarios: false,
    docs_pdf: true, docs_docx: false, docs_xlsx: false, docs_html: false,
    memory_retrieval: "lexical", semantic_model_ready: false, semantic_downloads_allowed: false,
  });
  view.rerender(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByText("Lexical (FTS5)")).toBeTruthy();
  expect(screen.getByText("PDF")).toBeTruthy();
  expect(screen.getByText("Not loaded · model downloads disabled")).toBeTruthy();
  useHaloStore.getState().applyFrame({
    type: "capabilities_state", id: "caps-ready", ts: "2026-09-09T00:00:00Z",
    voice_input: false, task_controls: true, skill_controls: false, demo_scenarios: false,
    docs_pdf: true, docs_docx: true, docs_xlsx: true, docs_html: true,
    memory_retrieval: "semantic", semantic_model_ready: true, semantic_downloads_allowed: false,
  });
  view.rerender(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByText("Semantic (local model)")).toBeTruthy();
  expect(screen.getByText("Loaded · model downloads disabled")).toBeTruthy();
  expect(screen.queryByText("Lexical (FTS5)")).toBeNull();
});

test("omitted download policy is unknown rather than disabled", () => {
  useHaloStore.getState().applyFrame({
    type: "capabilities_state", id: "partial-caps", ts: "2026-09-09T00:00:00Z",
    voice_input: false, task_controls: true, skill_controls: false, demo_scenarios: false,
    semantic_model_ready: true,
  });
  render(<SettingsView sendSettingsUpdate={vi.fn()} />);
  expect(screen.getByText("Loaded · model download policy unknown")).toBeTruthy();
  expect(screen.queryByText("Loaded · model downloads disabled")).toBeNull();
});
