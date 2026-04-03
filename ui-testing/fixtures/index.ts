import { test as base } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export interface TestState {
  users: Array<{ id: number; email: string; role: string }>;
  resources: Array<Record<string, unknown>>;
  tokens: { access: string };
  metadata: {
    generated_at: string;
    environment: string;
    base_url: string;
  };
}

// ---------------------------------------------------------------------------
// Fixtures personalizadas
// ---------------------------------------------------------------------------

type CustomFixtures = {
  testState: TestState;
  authenticatedPage: ReturnType<typeof base["extend"]>;
};

export const test = base.extend<CustomFixtures>({
  // Carga el estado generado por api-testing
  testState: async ({}, use) => {
    const stateFile = path.join(__dirname, "test-state.json");
    const exampleFile = path.join(__dirname, "test-state.example.json");

    let state: TestState = {
      users: [],
      resources: [],
      tokens: { access: "" },
      metadata: { generated_at: "", environment: "", base_url: "" },
    };

    if (fs.existsSync(stateFile)) {
      const raw = fs.readFileSync(stateFile, "utf-8");
      state = JSON.parse(raw);
    } else if (fs.existsSync(exampleFile)) {
      console.warn(
        "⚠️  test-state.json no encontrado — usando test-state.example.json"
      );
      const raw = fs.readFileSync(exampleFile, "utf-8");
      state = JSON.parse(raw);
    } else {
      console.warn(
        "⚠️  No se encontró test-state.json ni test-state.example.json"
      );
    }

    await use(state);
  },
});

export { expect } from "@playwright/test";
