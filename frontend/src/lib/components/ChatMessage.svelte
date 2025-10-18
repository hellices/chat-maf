<script lang="ts">
	import type { Message } from '$lib/types';

	export let message: Message;
	export let isLoading: boolean = false;
</script>

<style>
	.thinking-dot {
		animation: thinking 1.2s ease-in-out infinite;
	}
	
	.thinking-dot:nth-child(1) { animation-delay: 0s; }
	.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
	.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
	
	@keyframes thinking {
		0%, 60%, 100% {
			transform: scale(0.8);
			opacity: 0.3;
		}
		30% {
			transform: scale(1.2);
			opacity: 1;
		}
	}
</style>

<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
	<div class="max-w-xs lg:max-w-md px-4 py-3 rounded-2xl {message.role === 'user' 
		? 'bg-indigo-500 text-white' 
		: 'bg-slate-100 text-slate-800'}">
		<div class="text-xs font-medium mb-1 {message.role === 'user' ? 'text-indigo-100' : 'text-slate-500'}">
			{message.role === 'user' ? 'You' : 'Assistant'}
		</div>
		<div class="whitespace-pre-wrap break-words">
			{#if isLoading && !message.content}
				<div class="flex items-center space-x-2 text-slate-500">
					<div class="flex space-x-1">
						<div class="w-2 h-2 bg-indigo-400 rounded-full thinking-dot"></div>
						<div class="w-2 h-2 bg-indigo-400 rounded-full thinking-dot"></div>
						<div class="w-2 h-2 bg-indigo-400 rounded-full thinking-dot"></div>
					</div>
					<span class="text-sm">typing...</span>
				</div>
			{:else}
				{message.content}
			{/if}
		</div>
	</div>
</div>