<script lang="ts">
	import type { StreamingLog } from '$lib/stores/nl2sql';

	interface Props {
		logs: StreamingLog[];
		onToggle: (stepName: string) => void;
	}

	let { logs, onToggle }: Props = $props();
</script>

{#if logs.length > 0}
	<div class="streaming-logs space-y-2 my-4">
		{#each logs as log (log.stepName)}
			<div class="log-entry border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
				<!-- Header -->
				<button
					class="log-header w-full px-4 py-2 flex items-center justify-between bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					onclick={() => onToggle(log.stepName)}
					aria-expanded={log.isExpanded}
					aria-controls={`log-content-${log.stepName}`}
				>
					<div class="flex items-center gap-2">
						<span class="text-blue-600 dark:text-blue-400">
							{#if log.isExpanded}
								<!-- ChevronDown -->
								<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="6 9 12 15 18 9"></polyline>
								</svg>
							{:else}
								<!-- ChevronRight -->
								<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="9 18 15 12 9 6"></polyline>
								</svg>
							{/if}
						</span>
						<span class="font-medium text-gray-900 dark:text-gray-100">
							{log.stepLabel}
						</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							({log.content.length} chars)
						</span>
					</div>
					<span class="text-xs text-gray-400 dark:text-gray-500">
						{new Date(log.timestamp).toLocaleTimeString()}
					</span>
				</button>

				<!-- Content -->
				{#if log.isExpanded}
					<div
						id={`log-content-${log.stepName}`}
						class="log-content p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700"
					>
						<pre class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words font-mono overflow-x-auto">{log.content}</pre>
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}

<style>
	.streaming-logs {
		animation: fadeIn 0.3s ease-in-out;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.log-header {
		cursor: pointer;
		user-select: none;
	}

	.log-content pre {
		max-height: 400px;
		overflow-y: auto;
	}

	.log-content pre::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	.log-content pre::-webkit-scrollbar-track {
		background: rgba(0, 0, 0, 0.1);
		border-radius: 4px;
	}

	.log-content pre::-webkit-scrollbar-thumb {
		background: rgba(0, 0, 0, 0.3);
		border-radius: 4px;
	}

	.log-content pre::-webkit-scrollbar-thumb:hover {
		background: rgba(0, 0, 0, 0.5);
	}
</style>
