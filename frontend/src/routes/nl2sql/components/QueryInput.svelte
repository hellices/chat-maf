<script lang="ts">
	interface Props {
		message: string;
		isLoading: boolean;
		onSubmit: () => void;
		onMessageChange: (value: string) => void;
	}

	let { message, isLoading, onSubmit, onMessageChange }: Props = $props();

	function handleKeyPress(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			onSubmit();
		}
	}
</script>

<div class="border-t border-slate-200 p-4">
	<div class="flex gap-2">
		<textarea
			value={message}
			oninput={(e) => onMessageChange(e.currentTarget.value)}
			onkeypress={handleKeyPress}
			placeholder="Ask a question about your database..."
			class="flex-1 resize-none rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			rows="1"
			disabled={isLoading}
			aria-label="Query input"
			aria-describedby="query-hint"
		></textarea>
		<button
			onclick={onSubmit}
			disabled={isLoading || !message.trim()}
			class="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
			aria-label={isLoading ? 'Processing query' : 'Send query'}
		>
			{#if isLoading}
				<svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span>Thinking...</span>
			{:else}
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
				</svg>
				<span>Send</span>
			{/if}
		</button>
	</div>
</div>
