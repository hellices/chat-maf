import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('frontend-svelte');

/**
 * 함수 실행을 추적하는 헬퍼
 * @param name - span 이름
 * @param fn - 실행할 함수
 * @returns 함수 실행 결과
 */
export async function traceAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
	const span = tracer.startSpan(name);
	try {
		const result = await fn();
		span.end();
		return result;
	} catch (error) {
		span.recordException(error as Error);
		span.end();
		throw error;
	}
}

/**
 * 동기 함수 실행을 추적하는 헬퍼
 * @param name - span 이름
 * @param fn - 실행할 함수
 * @returns 함수 실행 결과
 */
export function traceSync<T>(name: string, fn: () => T): T {
	const span = tracer.startSpan(name);
	try {
		const result = fn();
		span.end();
		return result;
	} catch (error) {
		span.recordException(error as Error);
		span.end();
		throw error;
	}
}

/**
 * 속성과 함께 커스텀 span 생성
 * @param name - span 이름
 * @param attributes - span 속성
 */
export function createSpan(name: string, attributes?: Record<string, string | number | boolean>) {
	return tracer.startSpan(name, { attributes });
}

export { tracer };
