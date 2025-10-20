import { initTelemetry } from '$lib/telemetry';

// 브라우저에서만 실행
if (typeof window !== 'undefined') {
	initTelemetry();
}
