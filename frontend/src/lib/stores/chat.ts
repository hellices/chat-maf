import { writable, get, type Writable } from 'svelte/store';
import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { Message } from '../types';

export const messages: Writable<Message[]> = writable([]);
export const isLoading: Writable<boolean> = writable(false);
export const currentMessage: Writable<string> = writable('');
export const customInstruction: Writable<string> = writable('');

let abortController: AbortController | null = null;

async function streamResponse(endpoint: string, body: object): Promise<void> {
	if (get(isLoading)) return;

	isLoading.set(true);
	currentMessage.set('');
	abortController = new AbortController();

	try {
		const response = await fetch(`${PUBLIC_API_BASE_URL}${endpoint}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
			signal: abortController.signal
		});

		if (!response.ok) throw new Error('Failed to get response');

		const reader = response.body?.getReader();
		const decoder = new TextDecoder();

		if (reader) {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value, { stream: true });
				
				if (chunk) {
					messages.update(msgs => {
						const updated = [...msgs];
						updated[updated.length - 1].content += chunk;
						return updated;
					});
				}
			}
		}
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') return;
		
		messages.update(msgs => {
			const updated = [...msgs];
			updated[updated.length - 1].content = 'Error: Failed to get response from server';
			return updated;
		});
	} finally {
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