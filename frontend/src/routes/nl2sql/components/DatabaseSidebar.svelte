<script lang="ts">
	interface Props {
		databases: string[];
		selectedDatabase: string | null;
		loading: boolean;
		onSelectDatabase: (dbName: string) => void;
		onClose: () => void;
	}

	let { databases, selectedDatabase, loading, onSelectDatabase, onClose }: Props = $props();
</script>

<div class="w-64 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden" role="navigation" aria-label="Database selection">
	<div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
		<h3 class="font-semibold text-slate-900" id="database-sidebar-title">📊 Databases</h3>
		<button
			onclick={onClose}
			class="text-slate-400 hover:text-slate-600 transition-colors"
			title="Hide sidebar"
			aria-label="Hide database sidebar"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
			</svg>
		</button>
	</div>

	<div class="flex-1 overflow-y-auto p-3" role="listbox" aria-labelledby="database-sidebar-title">
		{#if loading}
			<div class="text-center py-8 text-slate-500 text-sm">
				<svg class="animate-spin h-5 w-5 mx-auto mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				Loading databases...
			</div>
		{:else if databases.length === 0}
			<div class="text-center py-8 text-slate-500 text-sm">
				No databases found
			</div>
		{:else}
			<div class="space-y-1">
				{#each databases as db}
					<button
						onclick={() => onSelectDatabase(db)}
						class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {selectedDatabase === db ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-slate-100 text-slate-700'}"
						role="option"
						aria-label="Select database {db}"
						aria-selected={selectedDatabase === db}
					>
						{db}
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
