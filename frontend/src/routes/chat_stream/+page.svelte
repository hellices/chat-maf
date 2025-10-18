<script lang="ts">
	import { onMount } from 'svelte';
	import { PUBLIC_API_BASE_URL } from '$env/static/public';

	let messages: Array<{role: 'user' | 'assistant', content: string}> = $state([]);
	let currentMessage = $state('');
	let isLoading = $state(false);
	let chatContainer: HTMLDivElement;

	async function sendMessage() {
		if (!currentMessage.trim() || isLoading) return;

		const userMessage = currentMessage.trim();
		currentMessage = '';
		isLoading = true;

		messages.push({ role: 'user', content: userMessage });
		messages.push({ role: 'assistant', content: '' });

		try {
			const response = await fetch(`${PUBLIC_API_BASE_URL}/chat`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ message: userMessage })
			});
			
			if (!response.ok) {
				throw new Error('Failed to get response');
			}

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
								messages[messages.length - 1].content += data;
								scrollToBottom();
							}
						}
					}
				}
			}
		} catch (error) {
			messages[messages.length - 1].content = 'Error: Failed to get response from server';
		} finally {
			isLoading = false;
		}
	}

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	onMount(() => {
		scrollToBottom();
	});
</script>

<div class="max-w-4xl mx-auto h-[calc(100vh-200px)] flex flex-col">
	<div class="bg-white rounded-lg shadow-md border border-gray-200 flex flex-col h-full">
		<div class="p-4 border-b border-gray-200">
			<h1 class="text-xl font-semibold text-gray-900">Chat Stream</h1>
			<p class="text-sm text-gray-600">Real-time chat with AI agent</p>
		</div>

		<div 
			bind:this={chatContainer}
			class="flex-1 overflow-y-auto p-4 space-y-4"
		>
			{#each messages as message}
				<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg {message.role === 'user' 
						? 'bg-blue-600 text-white' 
						: 'bg-gray-100 text-gray-900'}">
						<div class="text-xs font-medium mb-1 {message.role === 'user' ? 'text-blue-200' : 'text-gray-500'}">
							{message.role === 'user' ? 'You' : 'Assistant'}
						</div>
						<div class="whitespace-pre-wrap break-words">
							{message.content}
							{#if message.role === 'assistant' && !message.content && isLoading}
								<span class="inline-block w-2 h-4 bg-gray-400 animate-pulse"></span>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		<div class="p-4 border-t border-gray-200">
			<div class="flex space-x-2">
				<input
					type="text"
					bind:value={currentMessage}
					onkeypress={handleKeyPress}
					placeholder="Type your message..."
					disabled={isLoading}
					class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
				/>
				<button
					onclick={sendMessage}
					disabled={isLoading || !currentMessage.trim()}
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
				>
					{isLoading ? 'Sending...' : 'Send'}
				</button>
			</div>
		</div>
	</div>
</div>