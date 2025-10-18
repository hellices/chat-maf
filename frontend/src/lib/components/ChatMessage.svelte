<script lang="ts">
	import type { Message } from '$lib/types';

	interface Props {
		message: Message;
		isLoading?: boolean;
	}

	let { message, isLoading = false }: Props = $props();
</script>



<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'} mb-3">
	<div class="max-w-[28rem] px-3 py-2 rounded-2xl {message.role === 'user' 
		? 'bg-indigo-500 text-white' 
		: 'bg-slate-50 text-slate-800 border border-slate-200'}">
		<div class="text-xs font-medium mb-1 {message.role === 'user' ? 'text-indigo-100' : 'text-slate-500'}">
			{message.role === 'user' ? 'You' : 'Assistant'}
		</div>
		<div class="break-words text-sm leading-relaxed">
			{#if isLoading && !message.content}
				<div class="flex items-center space-x-2 text-slate-500">
					<div class="flex space-x-1">
						<div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0s;"></div>
						<div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.1s;"></div>
						<div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.2s;"></div>
					</div>
					<span class="text-xs">typing...</span>
				</div>
			{:else if message.role === 'assistant'}
				<div class="formatted-message" style="white-space: pre-wrap !important; line-height: 1.6 !important;">
					{message.content}
				</div>
			{:else}
				<div style="white-space: pre-wrap !important; line-height: 1.6 !important;">{message.content}</div>
			{/if}
		</div>
	</div>
</div>

<style>
	:global(.formatted-message) {
		white-space: pre-wrap !important;
		word-wrap: break-word !important;
		overflow-wrap: break-word !important;
	}
	
	:global(.formatted-message p) {
		margin-bottom: 0.75rem;
	}
	
	:global(.formatted-message p:last-child) {
		margin-bottom: 0;
	}
	
	:global(.formatted-message strong) {
		font-weight: 600;
		color: rgb(15 23 42); /* slate-900 */
	}
	
	:global(.formatted-message em) {
		font-style: italic;
		color: rgb(51 65 85); /* slate-700 */
	}
</style>