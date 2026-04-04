/**
 * Script k6 con salida nativa a InfluxDB Cloud.
 * Las métricas se envían en tiempo real durante la ejecución.
 *
 * Ejecutar con:
 *   k6 run tests/load/load-influx.js \
 *     --env BASE_URL=https://tu-api.com \
 *     --env INFLUX_URL=https://us-east-1-1.aws.cloud2.influxdata.com \
 *     --env INFLUX_TOKEN=tu-token \
 *     --env INFLUX_ORG=KPMG \
 *     --env INFLUX_BUCKET=testing-metrics \
 *     --out xk6-influxdb
 *
 * Requiere el plugin xk6-influxdb:
 *   https://github.com/grafana/xk6-output-influxdb
 *
 * Alternativa sin plugin — usar output experimental:
 *   k6 run ... --out experimental-prometheus-rw
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ---------------------------------------------------------------------------
// Métricas personalizadas — se envían automáticamente a InfluxDB
// ---------------------------------------------------------------------------

const errorRate = new Rate("custom_error_rate");
const responseTime = new Trend("custom_response_time_ms");
const requestCount = new Counter("custom_request_count");

// ---------------------------------------------------------------------------
// Configuración
// ---------------------------------------------------------------------------

export const options = {
  scenarios: {
    constant_load: {
      executor: "constant-vus",
      vus: 10,
      duration: "30s",
      tags: { scenario: "constant", source: "k6" },
    },
    ramp_up: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 20 },
        { duration: "20s", target: 20 },
        { duration: "10s", target: 0 },
      ],
      startTime: "35s",
      tags: { scenario: "ramp", source: "k6" },
    },
  },

  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
    custom_error_rate: ["rate<0.01"],
  },

  // Tags globales — aparecen en todos los puntos de InfluxDB
  tags: {
    project: "api-testing",
    environment: __ENV.ENV || "local",
  },
};

// ---------------------------------------------------------------------------
// Variables de entorno
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "https://tu-api.com";

const headers = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

// ---------------------------------------------------------------------------
// Función principal
// ---------------------------------------------------------------------------

export default function () {
  // Request principal
  const response = http.get(`${BASE_URL}/`, {
    headers,
    tags: { endpoint: "root", method: "GET" },
  });

  // Registrar métricas custom
  const success = response.status < 400;
  errorRate.add(!success);
  responseTime.add(response.timings.duration);
  requestCount.add(1);

  check(response, {
    "status < 400": (r) => r.status < 400,
    "response time < 500ms": (r) => r.timings.duration < 500,
    "has body": (r) => r.body && r.body.length > 0,
  });

  sleep(1);
}

// ---------------------------------------------------------------------------
// Resumen al finalizar — también escribe a InfluxDB via handleSummary
// ---------------------------------------------------------------------------

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    metrics: {
      http_req_duration_p95: data.metrics.http_req_duration?.values?.["p(95)"] || 0,
      http_req_duration_avg: data.metrics.http_req_duration?.values?.avg || 0,
      http_req_failed_rate: data.metrics.http_req_failed?.values?.rate || 0,
      http_reqs_count: data.metrics.http_reqs?.values?.count || 0,
      vus_max: data.metrics.vus_max?.values?.max || 0,
    },
  };

  return {
    "reports/k6-summary.json": JSON.stringify(summary, null, 2),
    "reports/k6-full-summary.json": JSON.stringify(data, null, 2),
    stdout: "\n",
  };
}
