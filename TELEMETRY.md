# OpenTelemetry Integration

This project integrates OpenTelemetry to collect telemetry from both frontend (Svelte) and backend (FastAPI) applications, visualized through Aspire Dashboard.

## Architecture

```
┌─────────────┐         ┌──────────────┐
│   Browser   │         │   FastAPI    │
│  (Svelte)   │         │   Backend    │
└──────┬──────┘         └──────┬───────┘
       │                       │
       │ Protobuf/HTTP         │ gRPC OTLP
       │ Port 4318             │ Port 4317
       │                       │
       ├───────────────────────┤
       ▼                       ▼
┌─────────────────────────────────┐
│      Aspire Dashboard           │
│  - Traces Visualization         │
│  - Metrics & Logs               │
│  - UI: Port 18888               │
└─────────────────────────────────┘
```

---

## Quick Start

### 1. Deploy Aspire Dashboard

**Local (Docker):**
```bash
docker run --rm -it -p 18888:18888 -p 18889:18889 -p 18890:18890 \
  -e DASHBOARD__OTLP__CORS__ALLOWEDORIGINS=http://localhost:5173 \
  -e DASHBOARD__OTLP__CORS__ALLOWEDHEADERS=* \
  mcr.microsoft.com/dotnet/aspire-dashboard:9.5
```

**AKS (Kubernetes):**
```bash
kubectl apply -f aspire-dashboard.yaml
kubectl get service aspire-dashboard --watch
```

Access Dashboard: `http://localhost:18888` or `http://<EXTERNAL-IP>:18888`

### 2. Configure Environment Variables

**Frontend** (`frontend/.env`):
```bash
PUBLIC_OTLP_ENABLED=true
PUBLIC_OTLP_ENDPOINT=http://localhost:18890/v1/traces
```

**Backend** (`backend/.env`):
```bash
OTLP_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### 3. Start Applications

```bash
# Frontend
cd frontend && npm run dev

# Backend
cd backend && uvicorn main:app --reload
```

---

## Frontend Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PUBLIC_OTLP_ENABLED` | Enable/disable telemetry | `true` or `false` |
| `PUBLIC_OTLP_ENDPOINT` | OTLP HTTP endpoint | `http://localhost:18890/v1/traces` |

### Automatic Instrumentation

The frontend automatically tracks:
- **Service Identity**: `frontend-svelte` v1.0.0
- **Fetch API**: All HTTP requests (URL, method, status, timing)
- **Page Load**: Document load, DOM construction, resource loading
- **User Events**: Click and form submission events

**Example**: See `src/lib/stores/chat.ts` for real-world usage with streaming responses.

---

## Backend Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OTLP_ENABLED` | Enable/disable telemetry | `true` or `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP gRPC endpoint | `http://localhost:4317` |

### Automatic Instrumentation

The backend automatically tracks:
- **Service Identity**: `backend-fastapi` v1.0.0
- **HTTP Requests**: All FastAPI endpoints (method, path, status, duration)
- **Streaming Responses**: Long-running streaming endpoints
- **Exceptions**: Automatic error recording with stack traces

**Implementation**: `FastAPIInstrumentor` automatically instruments all routes in `main.py`.

### Logging Integration

All `logger.info()`, `logger.error()`, etc. calls are automatically exported to Aspire Dashboard:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing request: {request_id}")
logger.error(f"Failed to process: {error}")
```

### Built-in OpenTelemetry

The backend uses **Microsoft Agent Framework** (v1.0.0b251016+), which includes:
- `opentelemetry-api` v1.38.0
- `opentelemetry-sdk` v1.38.0
- `opentelemetry-instrumentation-fastapi` v0.59b0
- OTLP exporters (gRPC/HTTP)

No additional package installation required.

---

## Aspire Dashboard Setup

### Port Configuration

| Port | Purpose | Used By |
|------|---------|---------|
| 18888 | Dashboard UI | Browser access |
| 4317 (→18889) | gRPC OTLP | Backend (FastAPI) |
| 4318 (→18890) | HTTP OTLP | Frontend (Browser) |

### CORS Configuration

For browser telemetry, CORS must be configured in `aspire-dashboard.yaml`:

```yaml
env:
- name: DASHBOARD__OTLP__CORS__ALLOWEDORIGINS
  value: "http://localhost:5173,http://localhost:4173,http://localhost:8000"
- name: DASHBOARD__OTLP__CORS__ALLOWEDHEADERS
  value: "*"
```

---

## Viewing Traces

1. Open Dashboard: `http://localhost:18888` (or AKS external IP)
2. Navigate to **Traces** tab
3. Filter by service:
   - `frontend-svelte` - Browser interactions
   - `backend-fastapi` - API requests
4. Click a trace to view detailed span timeline
5. Use search to find specific operations (e.g., `chat.streamResponse`)

---

## Troubleshooting

### CORS Errors (Frontend)

**Problem**: Browser console shows CORS errors

**Solution**: Add allowed origin and headers to Aspire Dashboard:
```yaml
env:
- name: DASHBOARD__OTLP__CORS__ALLOWEDORIGINS
  value: "http://localhost:5173,http://localhost:4173,http://localhost:8000"
- name: DASHBOARD__OTLP__CORS__ALLOWEDHEADERS
  value: "*"
```

### 415 Unsupported Media Type

**Problem**: Aspire rejects traces with 415 error

**Solution**: Frontend must use Protobuf exporter, not JSON:
```bash
npm install @opentelemetry/exporter-trace-otlp-proto
```

### No Traces Visible

**Checklist**:
1. ✅ `OTLP_ENABLED=true` in environment variables
2. ✅ Aspire Dashboard is running and accessible
3. ✅ Correct endpoint URLs (4317 for backend, 18890 for frontend)
4. ✅ Check browser/terminal console for initialization messages
5. ✅ Verify network requests to `/v1/traces` succeed (200 OK)

### Service Shows as `unknown_service`

**Problem**: Traces appear without proper service name

**Solution**: Ensure Resource configuration is set:

**Frontend**: Check `telemetry.ts` includes:
```typescript
const resource = resourceFromAttributes({
  [ATTR_SERVICE_NAME]: 'frontend-svelte',
  [ATTR_SERVICE_VERSION]: '1.0.0'
});
```

**Backend**: Check `otlp_tracing.py` includes:
```python
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: service_name,
    ResourceAttributes.SERVICE_VERSION: service_version,
})
```

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Frontend Traces | ✅ Complete | Protobuf OTLP, automatic instrumentation |
| Backend Traces | ✅ Complete | FastAPI auto-instrumentation |
| Backend Logs | ✅ Complete | Integrated with Python logging |
| Backend Metrics | ✅ Complete | Periodic metric export |
| Aspire Dashboard | ✅ Complete | AKS deployment with CORS |
| Custom Spans | ✅ Complete | Helper functions and examples |

---

## Additional Resources

- [OpenTelemetry JavaScript](https://opentelemetry.io/docs/languages/js/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Aspire Dashboard](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard)
- [Browser Telemetry Guide](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard/enable-browser-telemetry)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)

