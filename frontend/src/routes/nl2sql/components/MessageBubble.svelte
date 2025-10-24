<script lang="ts">
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface MessageData {
		role: 'user' | 'assistant';
		content: string;
		sql?: string;
		result?: any;
		database?: string;
		reasoning_evaluation?: {
			is_correct: boolean | null;
			confidence: number;
			explanation: string;
			suggestions: string;
		};
	}

	interface Props {
		message: MessageData;
	}

	let { message }: Props = $props();
</script>

{#if message.role === 'user'}
	<div class="flex justify-end">
		<div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] shadow-sm">
			<p class="text-[15px] leading-relaxed">{message.content}</p>
		</div>
	</div>
{:else}
	<div class="flex justify-start">
		<div class="bg-slate-100 text-slate-900 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%] shadow-sm">
			<div class="text-[15px] leading-relaxed">
				<MarkdownRenderer content={message.content} />
			</div>
			
			{#if message.database}
				<div class="mt-2 text-xs text-slate-500 flex items-center gap-1">
					<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
					</svg>
					<span>Database: <span class="font-medium text-slate-700">{message.database}</span></span>
				</div>
			{/if}
			
			{#if message.sql}
				<details class="mt-3 group">
					<summary class="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1.5">
						<svg class="w-3 h-3 transform group-open:rotate-90 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
						</svg>
						SQL Query
					</summary>
					<pre class="mt-2 text-xs bg-slate-900 text-green-400 p-3 rounded-lg overflow-x-auto"><code>{message.sql}</code></pre>
				</details>
			{/if}

			{#if message.reasoning_evaluation}
				<div class="mt-3 border border-slate-200 rounded-lg p-3 bg-white">
					<div class="flex items-start gap-2">
						{#if message.reasoning_evaluation.is_correct === true}
							<svg class="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						{:else if message.reasoning_evaluation.is_correct === false}
							<svg class="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
							</svg>
						{:else}
							<svg class="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						{/if}
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs font-semibold text-slate-700">Reasoning Quality</span>
								<span class="text-xs px-1.5 py-0.5 rounded-full font-medium {
									message.reasoning_evaluation.confidence >= 70 ? 'bg-green-100 text-green-700' :
									message.reasoning_evaluation.confidence >= 40 ? 'bg-amber-100 text-amber-700' :
									'bg-red-100 text-red-700'
								}">
									{message.reasoning_evaluation.confidence}%
								</span>
							</div>
							<p class="text-xs text-slate-600 leading-relaxed">{message.reasoning_evaluation.explanation}</p>
							{#if message.reasoning_evaluation.suggestions}
								<div class="mt-3 pt-3 border-t border-slate-200 bg-blue-50 -mx-3 -mb-3 px-3 py-3 rounded-b-lg">
									<div class="flex items-start gap-1.5 mb-2">
										<svg class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
										</svg>
										<span class="text-xs font-semibold text-blue-900">System Improvement Suggestions</span>
									</div>
									<div class="text-xs text-slate-700 leading-relaxed space-y-1 pl-5">
										{#each message.reasoning_evaluation.suggestions.split('\n').filter(line => line.trim()) as suggestion}
											<div class="flex items-start gap-1.5">
												{#if suggestion.trim().startsWith('•')}
													<span class="text-blue-600 font-bold flex-shrink-0">•</span>
													<span>{suggestion.trim().substring(1).trim()}</span>
												{:else}
													<span>{suggestion.trim()}</span>
												{/if}
											</div>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			{#if message.result}
				<details class="mt-2 group">
					<summary class="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1.5">
						<svg class="w-3 h-3 transform group-open:rotate-90 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
						</svg>
						Results
					</summary>
					<pre class="mt-2 text-xs bg-slate-900 text-slate-300 p-3 rounded-lg overflow-x-auto">{JSON.stringify(message.result, null, 2)}</pre>
				</details>
			{/if}
		</div>
	</div>
{/if}
