import { writable, get, type Writable } from 'svelte/store';
import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { Message } from '../types';

export const messages: Writable<Message[]> = writable([]);
export const isLoading: Writable<boolean> = writable(false);
export const currentMessage: Writable<string> = writable('');
export const customInstruction: Writable<string> = writable('');

let abortController: AbortController | null = null;

export const chatActions = {
	async sendMessage(message: string, instruction: string): Promise<void> {
		if (!message.trim() || get(isLoading)) return;

		isLoading.set(true);
		currentMessage.set('');
		
		messages.update(msgs => [
			...msgs,
			{ role: 'user', content: message.trim() },
			{ role: 'assistant', content: '' }
		]);

		abortController = new AbortController();

		try {
			const response = await fetch(`${PUBLIC_API_BASE_URL}/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message, instruction }),
				signal: abortController.signal
			});

			if (!response.ok) throw new Error('Failed to get response');

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();

			if (reader) {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					const chunk = decoder.decode(value);
					const lines = chunk.split('\n');

					for (const line of lines) {
						if (line.startsWith('data: ')) {
							const data = line.slice(6);
							if (data.trim()) {
								messages.update(msgs => {
									const updated = [...msgs];
									updated[updated.length - 1].content += data;
									return updated;
								});
							}
						}
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