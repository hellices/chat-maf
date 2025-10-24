/**
 * NL2SQL API Service
 * Handles all API communication for the NL2SQL feature.
 */

import { z } from 'zod';

// ===== Zod Schemas for Runtime Validation =====

// Agent Framework Events (from backend)
const WorkflowStatusEventSchema = z.object({
	type: z.literal('WorkflowStatusEvent'),
	timestamp: z.string(),
	executor_id: z.string().optional(),
	step_name: z.string().optional(),
	step_label: z.string().optional(),
	step_category: z.string().optional(),
	data: z.any().optional()
});

const ExecutorInvokedEventSchema = z.object({
	type: z.literal('ExecutorInvokedEvent'),
	timestamp: z.string(),
	executor_id: z.string(),
	step_name: z.string(),
	step_label: z.string().optional(),
	step_category: z.string().optional(),
	data: z.any().optional()
});

const ExecutorCompletedEventSchema = z.object({
	type: z.literal('ExecutorCompletedEvent'),
	timestamp: z.string(),
	executor_id: z.string(),
	step_name: z.string(),
	step_label: z.string().optional(),
	step_category: z.string().optional(),
	data: z.any().optional()
});

const AgentRunUpdateEventSchema = z.object({
	type: z.literal('AgentRunUpdateEvent'),
	timestamp: z.string(),
	executor_id: z.string(),
	step_name: z.string(),
	step_label: z.string().optional(),
	step_category: z.string().optional(),
	data: z.string().optional()
});

const WorkflowOutputEventSchema = z.object({
	type: z.literal('WorkflowOutputEvent'),
	timestamp: z.string(),
	executor_id: z.string().optional(),
	step_name: z.string().optional(),
	data: z.object({
		sql: z.string(),
		database: z.string(),
		execution_result: z.any(),
		natural_language_response: z.string().nullable().optional(),
		reasoning_evaluation: z.object({
			is_correct: z.boolean().nullable(),
			confidence: z.number(),
			explanation: z.string(),
			suggestions: z.string()
		}).nullable().optional()
	})
});

// Legacy progress event (keep for backwards compatibility)
const NL2SQLProgressEventSchema = z.object({
	type: z.literal('progress'),
	executor_id: z.string(),
	data: z
		.object({
			summary: z.string().optional()
		})
		.optional()
});

// Completion signal
const CompletionEventSchema = z.object({
	status: z.literal('completed'),
	type: z.string().optional()
});

// Error event
const NL2SQLErrorEventSchema = z.object({
	status: z.literal('error'),
	type: z.string().optional(),
	error: z.string().optional(),
	message: z.string().optional()
});

const NL2SQLEventSchema = z.union([
	WorkflowStatusEventSchema,
	ExecutorInvokedEventSchema,
	ExecutorCompletedEventSchema,
	AgentRunUpdateEventSchema,
	WorkflowOutputEventSchema,
	NL2SQLProgressEventSchema,
	CompletionEventSchema,
	NL2SQLErrorEventSchema
]);

// ===== TypeScript Types =====

export type WorkflowStatusEvent = z.infer<typeof WorkflowStatusEventSchema>;
export type ExecutorInvokedEvent = z.infer<typeof ExecutorInvokedEventSchema>;
export type ExecutorCompletedEvent = z.infer<typeof ExecutorCompletedEventSchema>;
export type AgentRunUpdateEvent = z.infer<typeof AgentRunUpdateEventSchema>;
export type WorkflowOutputEvent = z.infer<typeof WorkflowOutputEventSchema>;
export type NL2SQLProgressEvent = z.infer<typeof NL2SQLProgressEventSchema>;
export type CompletionEvent = z.infer<typeof CompletionEventSchema>;
export type NL2SQLErrorEvent = z.infer<typeof NL2SQLErrorEventSchema>;
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

						// Parse and validate with Zod
						const rawData = JSON.parse(jsonStr);
						const eventData = NL2SQLEventSchema.parse(rawData);

						// Yield the event
						yield eventData;

						// Check if completed or error to stop iteration
						if ('status' in eventData && (eventData.status === 'completed' || eventData.status === 'error')) {
							return;
						}
					} catch (e) {
						if (e instanceof z.ZodError) {
							console.warn('Event validation failed (ignoring):', e.issues);
							console.warn('Problematic line:', line);
						} else {
							console.error('Parse error:', e);
							console.error('Problematic line:', line);
						}
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
