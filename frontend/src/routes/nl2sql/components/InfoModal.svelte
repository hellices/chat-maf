<script lang="ts">
	interface Props {
		show: boolean;
		onClose: () => void;
	}

	let { show, onClose }: Props = $props();
</script>

{#if show}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div 
		class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
		onclick={onClose}
	>
		<div 
			class="bg-white rounded-xl shadow-lg max-w-3xl w-full"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
			tabindex="-1"
		>
			<!-- Modal Header -->
			<div class="bg-slate-50 border-b border-slate-200 px-6 py-4 rounded-t-xl">
				<div class="flex items-center justify-between">
					<h2 id="modal-title" class="text-lg font-semibold text-slate-900">About NL2SQL Playground</h2>
					<button
						onclick={onClose}
						class="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 transition-colors"
						aria-label="Close modal"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>

			<!-- Modal Content -->
			<div class="p-6 space-y-4">
				<!-- Introduction -->
				<div>
					<h3 class="font-semibold text-slate-900 mb-2">What is this?</h3>
					<p class="text-slate-600 text-sm leading-relaxed">
						An interactive playground for Natural Language to SQL (NL2SQL) conversion using the 
						<a href="https://github.com/taoyds/spider" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">Spider dataset</a>. 
						Convert your questions in natural language into executable SQL queries across 200+ diverse databases.
					</p>
				</div>

				<!-- How to Use -->
				<div>
					<h3 class="font-semibold text-slate-900 mb-2">How to Use</h3>
					<ol class="space-y-2 text-sm text-slate-600">
						<li class="flex gap-2">
							<span class="font-semibold text-slate-700 flex-shrink-0">1.</span>
							<span><strong>Select a database</strong> from the left sidebar (optional but recommended for accuracy)</span>
						</li>
						<li class="flex gap-2">
							<span class="font-semibold text-slate-700 flex-shrink-0">2.</span>
							<span><strong>Optionally select specific tables</strong> by clicking them in the schema diagram below</span>
						</li>
						<li class="flex gap-2">
							<span class="font-semibold text-slate-700 flex-shrink-0">3.</span>
							<span><strong>Ask your question</strong> in natural language and get SQL + results</span>
						</li>
					</ol>
				</div>

				<!-- Writing Questions -->
				<div>
					<h3 class="font-semibold text-slate-900 mb-2">Writing Effective Questions</h3>
					<div class="space-y-2 text-sm">
						<p class="text-slate-600">Reference table and column names when asking questions:</p>
						<div class="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
							<div>
								<div class="text-xs font-medium text-slate-500 mb-1">✓ Good Examples</div>
								<div class="space-y-1 text-slate-700">
									<div>• "How many singers are there?"</div>
									<div>• "List all stadium names with capacity over 50000"</div>
									<div>• "What's the average age of singers from France?"</div>
									<div>• "Show concerts in stadiums with highest capacity"</div>
								</div>
							</div>
							<div class="pt-2 border-t border-slate-200">
								<div class="text-xs font-medium text-slate-500 mb-1">✗ Avoid</div>
								<div class="space-y-1 text-slate-700">
									<div>• Vague questions: "Show me data" or "What do you have?"</div>
									<div>• Questions about non-existent tables or columns</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Important Notes -->
				<div>
					<h3 class="font-semibold text-slate-900 mb-2">Important Notes</h3>
					<ul class="space-y-1.5 text-sm text-slate-600">
						<li class="flex items-start gap-2">
							<svg class="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<span><strong>Database selection is optional</strong> but helps improve accuracy by providing context</span>
						</li>
						<li class="flex items-start gap-2">
							<svg class="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<span><strong>Table selection is also optional</strong> and useful for focusing on specific parts of large databases</span>
						</li>
						<li class="flex items-start gap-2">
							<svg class="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<span>Without database selection, queries may be less accurate or fail</span>
						</li>
						<li class="flex items-start gap-2">
							<svg class="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<span>Click on tables in the schema to see their columns and relationships</span>
						</li>
					</ul>
				</div>
			</div>

			<!-- Modal Footer -->
			<div class="border-t border-slate-200 px-6 py-4 bg-slate-50 rounded-b-xl">
				<button
					onclick={onClose}
					class="w-full px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-medium transition-colors"
				>
					Got it
				</button>
			</div>
		</div>
	</div>
{/if}
