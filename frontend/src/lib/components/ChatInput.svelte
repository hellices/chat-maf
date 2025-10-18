<script lang="ts">
	import { currentMessage, isLoading } from '$lib/stores/chat';

	interface Props {
		onsubmit?: () => void;
		oninterrupt?: () => void;
	}

	let { onsubmit, oninterrupt }: Props = $props();

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			onsubmit?.();
		}
	}
</script>

<div class="p-6 border-t border-slate-100">
	<div class="flex space-x-3">
		<input
			type="text"
			bind:value={$currentMessage}
			onkeypress={handleKeyPress}
			placeholder="Type your message..."
			disabled={$isLoading}
			class="flex-1 px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 disabled:bg-slate-50"
		/>
		{#if $isLoading}
			<button
				onclick={() => oninterrupt?.()}
				class="px-6 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 focus:ring-2 focus:ring-red-300 flex items-center space-x-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10h6v4H9z"/>
				</svg>
				<span>Stop</span>
			</button>
		{:else}
			<button
				onclick={() => onsubmit?.()}
				disabled={!$currentMessage.trim()}
				class="px-6 py-3 bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 focus:ring-2 focus:ring-indigo-300 disabled:bg-slate-300"
			>
				Send
			</button>
		{/if}
	</div>
</div>