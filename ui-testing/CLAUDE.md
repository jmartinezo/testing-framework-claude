# CLAUDE.md — ui-testing

## Descripción del proyecto

Repositorio de testing de UI y flujos E2E usando Playwright y TypeScript.

Este repo se ejecuta después de `api-testing` en el pipeline general. Consume
el artefacto `test-state.json` generado por `api-testing` para obtener los datos
de estado (IDs, tokens, usuarios creados) que necesita para ejecutar los tests
de UI sin depender de la UI para crear datos.

---

## Stack

| Capa | Herramienta | Propósito |
|---|---|---|
| UI / E2E | Playwright | Automatización de navegador |
| Lenguaje | TypeScript | Tipado estático, nativo en Playwright |
| Reporting | Allure + Playwright HTML | Resultados y trazas de navegador |
| CI/CD | GitHub Actions | Ejecución continua |
| Runtime | Node.js 20+ | Entorno de ejecución |

---

## Estructura

```
ui-testing/
├── CLAUDE.md
├── package.json
├── tsconfig.json
├── playwright.config.ts          # Configuración central de Playwright
├── .env.example                  # Variables de entorno requeridas
├── tests/
│   ├── e2e/                      # Tests de flujos completos
│   ├── smoke/                    # Tests críticos de humo
│   └── regression/               # Tests de regresión
├── pages/                        # Page Object Model (POM)
│   └── <Recurso>Page.ts          # Una clase por página/sección
├── fixtures/
│   ├── index.ts                  # Fixtures personalizadas de Playwright
│   └── test-state.json           # Artefacto recibido de api-testing
├── helpers/
│   └── state-loader.ts           # Carga y tipado de test-state.json
└── reports/
    ├── allure-results/           # Salida JSON para Allure
    └── playwright-report/        # Reporte HTML nativo de Playwright
```

---

## Variables de entorno

```bash
BASE_URL=https://tu-app.com       # URL base de la aplicación bajo prueba
ENV=staging                       # Entorno: local | staging | production
HEADLESS=true                     # true en CI, false para debug local
```

---

## Comandos habituales

### Playwright

```bash
# Instalar dependencias y navegadores
npm install
npx playwright install

# Ejecutar todos los tests
npx playwright test

# Solo smoke tests
npx playwright test tests/smoke/

# Solo E2E
npx playwright test tests/e2e/

# Modo headed (debug visual)
npx playwright test --headed

# UI mode (inspector interactivo)
npx playwright test --ui

# Un test específico
npx playwright test tests/e2e/login.spec.ts

# Con workers paralelos limitados
npx playwright test --workers=2
```

### Allure

```bash
# Generar reporte
allure generate reports/allure-results -o reports/allure-report --clean

# Abrir en navegador
allure open reports/allure-report
```

### TypeScript

```bash
# Verificar tipos sin compilar
npx tsc --noEmit

# Compilar
npx tsc
```

---

## Convenciones

### Naming

- Tests E2E: `<flujo>.spec.ts` — ej. `login.spec.ts`, `checkout.spec.ts`
- Page Objects: `<Recurso>Page.ts` — ej. `LoginPage.ts`, `ProductPage.ts`
- Fixtures: nombres descriptivos en camelCase — ej. `authenticatedUser`
- Helpers: camelCase — ej. `stateLoader.ts`

### Page Object Model (POM)

Toda interacción con la UI pasa por un Page Object. Los tests nunca usan
selectores directamente — siempre a través de métodos del POM.

```typescript
// ✅ correcto
await loginPage.fillCredentials(user.email, user.password);
await loginPage.submit();

// ❌ incorrecto
await page.fill('#email', user.email);
await page.click('button[type=submit]');
```

### Selectores

Preferencia en este orden:
1. `getByRole` — accesibilidad primero
2. `getByLabel` / `getByPlaceholder`
3. `getByTestId` — atributos `data-testid`
4. CSS selector — solo como último recurso

### Comentarios

- Comentarios inline en **español**
- Nombres de clases, métodos y variables en **inglés**

---

## Consumo de datos de api-testing

El fichero `fixtures/test-state.json` contiene los datos creados por `api-testing`.
Se carga al inicio de la suite mediante `helpers/state-loader.ts`.

```typescript
// helpers/state-loader.ts
import testState from '../fixtures/test-state.json';

export const getTestUser = () => testState.users[0];
export const getTestProduct = () => testState.products[0];
```

En CI, GitHub Actions descarga el artefacto de `api-testing` y lo coloca
automáticamente en `fixtures/test-state.json` antes de ejecutar los tests.

En local, generarlo manualmente ejecutando `api-testing` primero, o usar
el fichero de ejemplo en `fixtures/test-state.example.json`.

---

## Configuración de Playwright (`playwright.config.ts`)

Aspectos clave de la configuración:

- `baseURL` viene de la variable de entorno `BASE_URL`
- `headless` viene de la variable de entorno `HEADLESS`
- Reporters configurados: Allure + HTML nativo
- Reintentos en CI: 2 reintentos automáticos
- Trazas activadas en el primer reintento (`on-first-retry`)
- Screenshots en fallo

---

## Pipeline GitHub Actions

Este repo se ejecuta **después** de `api-testing`. El workflow descarga
el artefacto `test-state.json` antes de arrancar Playwright.

| Job | Trigger |
|---|---|
| `download-state` | Descarga artefacto de api-testing |
| `smoke-tests` | push / PR |
| `e2e-tests` | push / PR |
| `regression-tests` | push a main / nightly |

---

## MCP Servers conectados

| Server | Propósito |
|---|---|
| `playwright-mcp` | Ejecutar tests, leer fallos, analizar trazas |
| `xray-export-mcp` | Generar casos de prueba CSV desde historias de usuario |

```bash
# Registrar en Claude Code
claude mcp add --transport stdio playwright-mcp -- node mcp/playwright_server.js
claude mcp add --transport stdio xray-export-mcp -- node mcp/xray_server.js
```

---

## Notas para Claude

- Todo el código es **TypeScript** — nunca JavaScript plano.
- Seguir siempre el patrón **Page Object Model** — ningún selector en los tests.
- Los selectores preferidos son `getByRole` y `getByTestId` — evitar CSS selectors.
- `BASE_URL` siempre de variable de entorno — nunca hardcodeada.
- Los datos de prueba vienen de `fixtures/test-state.json` — nunca crearlos en los tests de UI.
- Este repo no tiene nada de Python — es TypeScript/Node puro.
- Allure espera resultados en `reports/allure-results/` — no cambiar esta ruta.
- Para debug local usar `--headed` o `--ui` — nunca cambiar la config global a headed.
