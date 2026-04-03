/**
 * Script de load testing con k6.
 * Ejecutar con: k6 run tests/load/load.js --env BASE_URL=https://tu-api.com
 *
 * Documentación k6: https://k6.io/docs/
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Métricas personalizadas
// ---------------------------------------------------------------------------

// Tasa de errores custom (además de la built-in http_req_failed)
const errorRate = new Rate("custom_error_rate");

// Tiempo de respuesta por endpoint
const responseTime = new Trend("custom_response_time");

// ---------------------------------------------------------------------------
// Configuración del test
// ---------------------------------------------------------------------------

export const options = {
  // Escenarios de carga
  scenarios: {
    // Carga constante — baseline
    constant_load: {
      executor: "constant-vus",
      vus: 10,
      duration: "30s",
      tags: { scenario: "constant" },
    },
    // Rampa — simula incremento gradual de usuarios
    ramp_up: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 20 },  // subir a 20 usuarios
        { duration: "20s", target: 20 },  // mantener
        { duration: "10s", target: 0 },   // bajar
      ],
      startTime: "35s",  // empieza después del constant_load
      tags: { scenario: "ramp" },
    },
  },

  // Thresholds — el test falla si no se cumplen
  thresholds: {
    // P95 de tiempo de respuesta < 500ms
    http_req_duration: ["p(95)<500"],
    // Tasa de error < 1%
    http_req_failed: ["rate<0.01"],
    // Métrica custom
    custom_error_rate: ["rate<0.01"],
  },
};

// ---------------------------------------------------------------------------
// Configuración de entorno
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "https://tu-api.com";

// Cabeceras comunes
const headers = {
  "Accept": "application/json",
  "Content-Type": "application/json",
};

// ---------------------------------------------------------------------------
// Función principal — se ejecuta por cada VU en cada iteración
// ---------------------------------------------------------------------------

export default function () {
  // Test 1: endpoint principal
  const listResponse = http.get(`${BASE_URL}/`, { headers, tags: { endpoint: "list" } });

  check(listResponse, {
    "list: status 200": (r) => r.status === 200,
    "list: tiene body": (r) => r.body && r.body.length > 0,
    "list: respuesta < 500ms": (r) => r.timings.duration < 500,
  });

  errorRate.add(listResponse.status >= 400);
  responseTime.add(listResponse.timings.duration);

  // Pausa entre iteraciones — simula comportamiento real de usuario
  sleep(1);
}

// ---------------------------------------------------------------------------
// Resumen personalizado al finalizar
// ---------------------------------------------------------------------------

export function handleSummary(data) {
  return {
    // Guardar resumen JSON para análisis posterior
    "reports/k6-summary.json": JSON.stringify(data, null, 2),
    // Mostrar resumen en consola (comportamiento por defecto)
    stdout: "\n",
  };
}
