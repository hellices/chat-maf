<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { messages, isLoading } from '$lib/stores/chat';
	import ChatMessage from './ChatMessage.svelte';

	let messageContainer: HTMLElement;

	export function scrollToBottom() {
		if (messageContainer) {
			messageContainer.scrollTop = messageContainer.scrollHeight;
		}
	}

	$: if ($messages.length > 0) {
		tick().then(scrollToBottom);
	}
</script>

<div
	bind:this={messageContainer}
	class="flex-1 overflow-y-auto p-6 space-y-4"
>
	{#each $messages as message, index}
		<ChatMessage {message} isLoading={$isLoading && index === $messages.length - 1 && message.role === 'assistant' && !message.content} />
	{/each}
</div>