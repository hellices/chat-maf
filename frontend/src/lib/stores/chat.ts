import { writable, get, type Writable } from 'svelte/store';
import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { Message } from '../types';
import { traceAsync, createSpan } from '$lib/trace-helpers';

export const messages: Writable<Message[]> = writable([]);
export const isLoading: Writable<boolean> = writable(false);
export const isThinking: Writable<boolean> = writable(false);
export const currentMessage: Writable<string> = writable('');
export const customInstruction: Writable<string> = writable('');

let abortController: AbortController | null = null;
let thinkingTimer: ReturnType<typeof setTimeout> | null = null;

function startThinkingTimer() {
	// Clear any existing timer
	if (thinkingTimer) {
		clearTimeout(thinkingTimer);
	}
	
	// Set thinking to true after 1 second of no data
	thinkingTimer = setTimeout(() => {
		isThinking.set(true);
	}, 1000);
}

function resetThinkingTimer() {
	if (thinkingTimer) {
		clearTimeout(thinkingTimer);
		thinkingTimer = null;
	}
	isThinking.set(false);
}

async function streamResponse(endpoint: string, body: object): Promise<void> {
	if (get(isLoading)) return;

	const span = createSpan('chat.streamResponse', {
		endpoint,
		bodySize: JSON.stringify(body).length
	});

	isLoading.set(true);
	isThinking.set(false);
	currentMessage.set('');
	abortController = new AbortController();

	// Start the thinking timer immediately
	startThinkingTimer();

	try {
		const response = await fetch(`${PUBLIC_API_BASE_URL}${endpoint}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
			signal: abortController.signal
		});

		if (!response.ok) {
			span.setAttribute('error', true);
			span.setAttribute('http.status_code', response.status);
			throw new Error('Failed to get response');
		}

		span.setAttribute('http.status_code', response.status);

		const reader = response.body?.getReader();
		const decoder = new TextDecoder();

		if (reader) {
			let totalChunks = 0;
			while (true) {
				const { done, value } = await reader.read();
				if (done) {
					// Flush any remaining bytes in the decoder
					const finalChunk = decoder.decode();
					if (finalChunk) {
						messages.update(msgs => {
							const updated = [...msgs];
							updated[updated.length - 1].content += finalChunk;
							return updated;
						});
					}
					break;
				}

				totalChunks++;
				// The stream: true option ensures incomplete multibyte sequences
				// are buffered and carried over to the next chunk
				const chunk = decoder.decode(value, { stream: true });
				
				if (chunk) {
					// Reset thinking timer when we receive data
					resetThinkingTimer();
					
					messages.update(msgs => {
						const updated = [...msgs];
						updated[updated.length - 1].content += chunk;
						return updated;
					});
					
					// Start thinking timer again for next chunk
					startThinkingTimer();
				}
			}
			span.setAttribute('total_chunks', totalChunks);
		}
		span.end();
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') {
			span.setAttribute('aborted', true);
			span.end();
			return;
		}
		
		span.recordException(error as Error);
		span.end();
		
		messages.update(msgs => {
			const updated = [...msgs];
			updated[updated.length - 1].content = 'Error: Failed to get response from server';
			return updated;
		});
	} finally {
		resetThinkingTimer();
		isLoading.set(false);
		abortController = null;
	}
}

export const chatActions = {
	async sendInstructionMessage(message: string, instruction: string): Promise<void> {
		if (!message.trim()) return;

		messages.update(msgs => [
			...msgs,
			{ role: 'user', content: message.trim() },
			{ role: 'assistant', content: '' }
		]);

		await streamResponse('/instruction', { message, instruction });
	},

	async sendWebsiteAssistantMessage(message: string, url: string): Promise<void> {
		if (!message.trim()) return;

		messages.update(msgs => [
			...msgs,
			{ role: 'user', content: message.trim() },
			{ role: 'assistant', content: '' }
		]);

		await streamResponse('/website-assistant', { message, url });
	},

	interrupt(): void {
		if (abortController) {
			abortController.abort();
			abortController = null;
			resetThinkingTimer();
			isLoading.set(false);
			
			messages.update(msgs => {
				if (msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant') {
					const updated = [...msgs];
					updated[updated.length - 1].content += '\n\n[Response interrupted by user]';
					return updated;
				}
				return msgs;
			});
		}
	}
};