import * as fs from "fs";
import * as path from "path";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export interface TestUser {
  id: number;
  email: string;
  role: string;
}

export interface TestTokens {
  access: string;
}

export interface TestState {
  users: TestUser[];
  resources: Array<Record<string, unknown>>;
  tokens: TestTokens;
  metadata: {
    generated_at: string;
    environment: string;
    base_url: string;
  };
}

// ---------------------------------------------------------------------------
// Carga del estado
// ---------------------------------------------------------------------------

const STATE_FILE = path.join(__dirname, "../fixtures/test-state.json");
const EXAMPLE_FILE = path.join(
  __dirname,
  "../fixtures/test-state.example.json"
);

function loadState(): TestState {
  if (fs.existsSync(STATE_FILE)) {
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
  }
  if (fs.existsSync(EXAMPLE_FILE)) {
    console.warn("⚠️  Usando test-state.example.json — datos de ejemplo");
    return JSON.parse(fs.readFileSync(EXAMPLE_FILE, "utf-8"));
  }
  throw new Error(
    "No se encontró test-state.json. Ejecuta api-testing primero."
  );
}

const state = loadState();

// ---------------------------------------------------------------------------
// Accesores tipados
// ---------------------------------------------------------------------------

/**
 * Devuelve el primer usuario de prueba disponible.
 */
export function getTestUser(index = 0): TestUser {
  const user = state.users[index];
  if (!user) {
    throw new Error(`No hay usuario en el índice ${index} del test state.`);
  }
  return user;
}

/**
 * Devuelve todos los usuarios de prueba.
 */
export function getAllTestUsers(): TestUser[] {
  return state.users;
}

/**
 * Devuelve los tokens de acceso generados por api-testing.
 */
export function getTokens(): TestTokens {
  return state.tokens;
}

/**
 * Devuelve el estado completo.
 */
export function getFullState(): TestState {
  return state;
}
