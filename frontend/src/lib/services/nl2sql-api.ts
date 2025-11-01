/**
 * NL2SQL API Service
 * Handles all API communication for the NL2SQL feature.
 */

import { z } from 'zod';

// ===== Zod Schemas for Runtime Validation =====

// Base event - all events have at least a type
const BaseEventSchema = z.object({
	type: z.string(),
	origin: z.string().optional(), // RUNNER or EXECUTOR
	state: z.string().optional(), // WorkflowRunState
	executor_id: z.string().optional(),
	step_label: z.string().optional(),
	step_category: z.string().optional()
});

// Workflow output - the final result
const WorkflowOutputEventSchema = z.object({
	type: z.literal('WorkflowOutputEvent'),
	data: z.object({
		sql: z.string(),
		database: z.string(),
		execution_result: z.any(),
		natural_language_response: z.string().nullable().optional(),
		reasoning_evaluation: z
			.object({
				is_correct: z.boolean().nullable(),
				confidence: z.number(),
				explanation: z.string(),
				suggestions: z.string()
			})
			.nullable()
			.optional()
	})
});

// Completion signal
const CompletionEventSchema = z.object({
	status: z.literal('completed')
});

// Error event
const ErrorEventSchema = z.object({
	status: z.literal('error'),
	error: z.string().optional(),
	message: z.string().optional()
});

// Union of all events - use discriminated union for specific events, passthrough for others
const NL2SQLEventSchema = z.union([
	WorkflowOutputEventSchema,
	CompletionEventSchema,
	ErrorEventSchema,
	BaseEventSchema.passthrough() // Accept any other event with additional fields
]);

// ===== TypeScript Types =====

export type BaseEvent = z.infer<typeof BaseEventSchema>;
export type WorkflowOutputEvent = z.infer<typeof WorkflowOutputEventSchema>;
export type CompletionEvent = z.infer<typeof CompletionEventSchema>;
export type ErrorEvent = z.infer<typeof ErrorEventSchema>;
export type NL2SQLEvent = z.infer<typeof NL2SQLEventSchema>;

export interface NL2SQLQueryParams {
	message: string;
	selected_database?: string | null;
	selected_tables?: string[];
}

export class NL2SQLApiService {
	private baseUrl: string;

	constructor(baseUrl: string = 'http://localhost:8000') {
		this.baseUrl = baseUrl;
	}

	/**
	 * Stream NL2SQL query results.
	 * Yields events as they arrive from the backend.
	 */
	async *streamQuery(params: NL2SQLQueryParams): AsyncGenerator<NL2SQLEvent> {
		const response = await fetch(`${this.baseUrl}/nl2sql`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				message: params.message,
				selected_database: params.selected_database,
				selected_tables: params.selected_tables && params.selected_tables.length > 0 
					? params.selected_tables 
					: undefined
			})
		});

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		const reader = response.body?.getReader();
		if (!reader) {
			throw new Error('No reader available');
		}

		const decoder = new TextDecoder();
		let buffer = '';

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value);

			// Split by newlines but keep incomplete lines in buffer
			const lines = buffer.split('\n');

			if (!buffer.endsWith('\n')) {
				buffer = lines.pop() || '';
			} else {
				buffer = '';
			}

			for (const line of lines) {
				if (line.startsWith('data: ')) {
					try {
						const jsonStr = line.substring(6).trim();
						if (!jsonStr) continue;

						// Parse JSON
						const rawData = JSON.parse(jsonStr);
						
						// Validate with Zod (but allow unknown fields to pass through)
						const eventData = NL2SQLEventSchema.parse(rawData);

						// Yield the event
						yield eventData;

						// Check if completed or error to stop iteration
						if ('status' in eventData && (eventData.status === 'completed' || eventData.status === 'error')) {
							return;
						}
					} catch (e) {
						// Log but continue - don't break the stream
						console.warn('Event parse/validation error:', e);
						console.warn('Problematic line:', line);
					}
				}
			}
		}
	}

	/**
	 * Get list of available databases.
	 */
	async getDatabases(): Promise<string[]> {
		const response = await fetch(`${this.baseUrl}/spider/databases`);
		if (!response.ok) {
			throw new Error(`Failed to fetch databases: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Get database schema with relationships.
	 */
	async getDatabaseRelationships(dbName: string): Promise<any> {
		const response = await fetch(`${this.baseUrl}/spider/databases/${dbName}/relationships`);
		if (!response.ok) {
			throw new Error(`Failed to fetch schema for ${dbName}: ${response.status}`);
		}
		return response.json();
	}
}

// Singleton instance
export const nl2sqlApi = new NL2SQLApiService();
