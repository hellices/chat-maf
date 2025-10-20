import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-proto';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { PUBLIC_OTLP_ENABLED, PUBLIC_OTLP_ENDPOINT } from '$env/static/public';

let isInitialized = false;

export function initTelemetry() {
	// OTLP가 비활성화되어 있으면 건너뜀
	if (PUBLIC_OTLP_ENABLED !== 'true') {
		console.log('OpenTelemetry is disabled (PUBLIC_OTLP_ENABLED is not true)');
		return;
	}

	// 엔드포인트가 설정되지 않았으면 건너뜀
	if (!PUBLIC_OTLP_ENDPOINT) {
		console.log('OpenTelemetry is disabled (PUBLIC_OTLP_ENDPOINT is not set)');
		return;
	}

	// 이미 초기화되었으면 건너뜀
	if (isInitialized) {
		console.log('Telemetry already initialized');
		return;
	}

	try {
		// OTLP Exporter 설정 - Aspire Dashboard로 전송 (Protobuf)
		const exporter = new OTLPTraceExporter({
			url: PUBLIC_OTLP_ENDPOINT,
			headers: {}
		});

		// Batch Span Processor 생성
		const spanProcessor = new BatchSpanProcessor(exporter);

		// Resource 생성 (서비스 이름 정의)
		const resource = resourceFromAttributes({
			[ATTR_SERVICE_NAME]: 'frontend-svelte',
			[ATTR_SERVICE_VERSION]: '1.0.0'
		});

		// Tracer Provider 생성
		const provider = new WebTracerProvider({
			resource: resource,
			spanProcessors: [spanProcessor]
		});

		// OTLP 엔드포인트의 호스트를 추출하여 CORS 패턴에 추가
		const otlpUrl = new URL(PUBLIC_OTLP_ENDPOINT);
		const otlpHost = otlpUrl.host;

		// Provider 등록 (Context Manager 포함)
		provider.register({
			contextManager: new ZoneContextManager()
		});

		// 자동 계측 등록
		registerInstrumentations({
			instrumentations: [
				// Fetch API 호출 자동 추적
				new FetchInstrumentation({
					propagateTraceHeaderCorsUrls: [
						/localhost:8000/,
						new RegExp(otlpHost.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
					],
					clearTimingResources: true
				}),
				// 페이지 로드 성능 추적
				new DocumentLoadInstrumentation(),
				// 사용자 클릭, 인터랙션 추적
				new UserInteractionInstrumentation({
					eventNames: ['click', 'submit']
				})
			]
		});

		isInitialized = true;
		console.log(`OpenTelemetry initialized successfully. Endpoint: ${PUBLIC_OTLP_ENDPOINT}`);
	} catch (error) {
		console.error('Failed to initialize OpenTelemetry:', error);
	}
}

// 커스텀 span 생성을 위한 헬퍼 함수
export { trace } from '@opentelemetry/api';
