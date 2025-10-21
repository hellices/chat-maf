<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchTableSample } from '$lib/stores/spider-api';
	import type { DatabaseSchema, Relationship } from '$lib/types';

	let { 
		schema = $bindable(),
		selectedTables = $bindable([]),
		onTableClick
	}: { 
		schema: DatabaseSchema | null;
		selectedTables?: string[];
		onTableClick?: (tableName: string) => void;
	} = $props();
	
	let containerEl = $state<HTMLDivElement>();
	let relationships = $derived(extractRelationships(schema));
	let expandedTables = $state<Set<string>>(new Set());
	let tableSampleData = $state<Map<string, { columns: string[]; rows: any[] }>>(new Map());
	let loadingSamples = $state<Set<string>>(new Set());
	
	function handleTableClick(tableName: string) {
		if (onTableClick) {
			onTableClick(tableName);
		}
	}
	
	function toggleTableExpansion(tableName: string, event: Event) {
		event.stopPropagation();
		const newExpanded = new Set(expandedTables);
		if (newExpanded.has(tableName)) {
			newExpanded.delete(tableName);
		} else {
			newExpanded.add(tableName);
			// Fetch sample data when expanding table
			if (!tableSampleData.has(tableName)) {
				fetchSampleData(tableName);
			}
		}
		expandedTables = newExpanded;
	}

	async function fetchSampleData(tableName: string) {
		if (loadingSamples.has(tableName) || !schema) return;
		
		loadingSamples.add(tableName);
		loadingSamples = new Set(loadingSamples);
		
		try {
			const data = await fetchTableSample(schema.database, tableName, 5);
			tableSampleData.set(tableName, {
				columns: data.columns,
				rows: data.rows
			});
			tableSampleData = new Map(tableSampleData);
		} catch (error) {
			console.error(`Failed to fetch sample data for ${tableName}:`, error);
		} finally {
			loadingSamples.delete(tableName);
			loadingSamples = new Set(loadingSamples);
		}
	}
	
	function isTableExpanded(tableName: string): boolean {
		return expandedTables.has(tableName);
	}
	
	function isTableSelected(tableName: string): boolean {
		return selectedTables ? selectedTables.includes(tableName) : false;
	}
	
	function handleTableKeyDown(event: KeyboardEvent, tableName: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleTableClick(tableName);
		}
	}

	function extractRelationships(schema: DatabaseSchema | null): Relationship[] {
		if (!schema) return [];
		
		const rels: Relationship[] = [];
		schema.tables.forEach(table => {
			table.columns.forEach(column => {
				if (column.foreign_key) {
					rels.push({
						from: { table: table.name, column: column.name },
						to: { table: column.foreign_key.table, column: column.foreign_key.column }
					});
				}
			});
		});
		return rels;
	}

	onMount(() => {
		// Any future canvas/SVG drawing logic could go here
	});
</script>

{#if schema && schema.tables.length > 0}
	<div class="space-y-3" bind:this={containerEl}>
		<!-- Header with Stats -->
		<div class="flex items-center justify-between mb-2">
			<h4 class="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"
					/>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 4v16M15 4v16M4 9h16M4 15h16"
					/>
				</svg>
				Schema Diagram
			</h4>
			<div class="flex items-center gap-3 text-xs text-slate-500">
				<span class="flex items-center gap-1">
					<span class="w-2 h-2 bg-blue-500 rounded-full"></span>
					{schema.tables.length} tables
				</span>
				{#if relationships.length > 0}
					<span class="flex items-center gap-1">
						<span class="w-2 h-2 bg-green-500 rounded-full"></span>
						{relationships.length} relations
					</span>
				{/if}
			</div>
		</div>

		<!-- Relationship Summary (if exists) -->
		{#if relationships.length > 0}
			<details class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200">
				<summary class="cursor-pointer px-3 py-2 text-xs font-semibold text-green-800 flex items-center gap-1.5 hover:bg-green-100/50 transition-colors">
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
					<span>Table Relationships ({relationships.length})</span>
					<svg class="w-3 h-3 ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</summary>
				<div class="px-3 pb-3 pt-2 space-y-1">
					{#each relationships as rel}
						<div class="text-xs text-green-700 font-mono flex items-center gap-1.5 py-0.5">
							<span class="font-semibold">{rel.from.table}</span>
							<span class="text-green-500 text-[10px]">({rel.from.column})</span>
							<svg class="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
							</svg>
							<span class="font-semibold">{rel.to.table}</span>
							<span class="text-green-500 text-[10px]">({rel.to.column})</span>
						</div>
					{/each}
				</div>
			</details>
		{/if}

		<!-- Tables Grid - ERwin Style -->
		<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
			{#each schema.tables as table}
				<div 
					class="border-2 rounded-lg overflow-hidden bg-white shadow-sm hover:shadow-md transition-all {isTableSelected(table.name) ? 'border-green-500 ring-2 ring-green-200' : 'border-slate-300 hover:border-blue-400'}"
				>
					<!-- Table Header - Compact -->
					<div 
						class="px-3 py-2 flex items-center justify-between cursor-pointer {isTableSelected(table.name) ? 'bg-gradient-to-r from-green-600 to-green-700' : 'bg-gradient-to-r from-blue-600 to-blue-700'}"
						onclick={(e) => toggleTableExpansion(table.name, e)}
						onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), toggleTableExpansion(table.name, e))}
						role="button"
						tabindex="0"
					>
						<div class="flex items-center gap-2 flex-1 min-w-0">
							<button 
								onclick={(e) => { e.stopPropagation(); handleTableClick(table.name); }}
								class="flex-shrink-0 hover:bg-white/20 rounded p-0.5 transition-colors"
								title={isTableSelected(table.name) ? "Deselect table" : "Select table"}
							>
								{#if isTableSelected(table.name)}
									<svg class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
								{:else}
									<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
									</svg>
								{/if}
							</button>
							<span class="font-bold text-white text-xs tracking-wide truncate" title={table.name}>
								{table.name}
							</span>
						</div>
						<div class="flex items-center gap-1.5 flex-shrink-0">
							<span class="text-[10px] text-white/80 font-medium">
								{table.columns.length}
							</span>
							<svg 
								class="w-3 h-3 text-white transition-transform {isTableExpanded(table.name) ? 'rotate-180' : ''}" 
								fill="none" 
								stroke="currentColor" 
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
						</div>
					</div>

					<!-- Columns - Expandable -->
					{#if isTableExpanded(table.name)}
						<div class="max-h-64 overflow-y-auto bg-slate-50">
							<div class="divide-y divide-slate-200">
								{#each table.columns as column}
									<div class="px-3 py-1.5 hover:bg-blue-50 transition-colors">
										<div class="flex items-center justify-between gap-2">
											<div class="flex items-center gap-1.5 min-w-0 flex-1">
												<!-- Column Icon -->
												{#if column.primary_key}
													<svg class="w-2.5 h-2.5 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M18 8a6 6 0 01-7.743 5.743L10 14l-1 1-1 1H6v2H2v-4l4.257-4.257A6 6 0 1118 8zm-6-4a1 1 0 100 2 2 2 0 012 2 1 1 0 102 0 4 4 0 00-4-4z" clip-rule="evenodd" />
													</svg>
												{:else if column.foreign_key}
													<svg class="w-2.5 h-2.5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clip-rule="evenodd" />
													</svg>
												{:else}
													<div class="w-1.5 h-1.5 bg-slate-400 rounded-full flex-shrink-0"></div>
												{/if}
												
												<span class="text-[11px] font-mono truncate {column.primary_key ? 'font-bold text-slate-900' : 'text-slate-700'}" title={column.name}>
													{column.name}
												</span>
											</div>
											<span class="text-[10px] text-slate-500 font-mono flex-shrink-0">
												{column.type.split('(')[0]}
											</span>
										</div>
										
										{#if column.foreign_key}
											<div class="ml-4 mt-0.5 flex items-center gap-1 text-[10px] text-green-600">
												<svg class="w-2 h-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 7l5 5m0 0l-5 5m5-5H6" />
												</svg>
												<span class="font-mono truncate" title="{column.foreign_key.table}.{column.foreign_key.column}">
													{column.foreign_key.table}.{column.foreign_key.column}
												</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>

						<!-- Sample Data Section -->
						{#if loadingSamples.has(table.name)}
							<div class="px-3 py-2 bg-blue-50 border-t border-blue-100">
								<div class="flex items-center gap-2 text-xs text-blue-600">
									<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									<span>Loading sample data...</span>
								</div>
							</div>
						{:else if tableSampleData.has(table.name)}
							{@const sampleData = tableSampleData.get(table.name)}
							<div class="border-t border-slate-200">
								<details class="group">
									<summary class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 cursor-pointer transition-colors flex items-center justify-between">
										<span class="text-[10px] font-medium text-slate-700">Sample Data (5 rows)</span>
										<svg class="w-3 h-3 text-slate-500 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
										</svg>
									</summary>
									<div class="max-h-48 overflow-auto bg-white">
										<table class="w-full text-[10px]">
											<thead class="bg-slate-50 sticky top-0">
												<tr>
													{#each sampleData?.columns || [] as col}
														<th class="px-2 py-1 text-left font-medium text-slate-700 border-b border-slate-200">
															{col}
														</th>
													{/each}
												</tr>
											</thead>
											<tbody class="divide-y divide-slate-100">
												{#each sampleData?.rows || [] as row}
													<tr class="hover:bg-blue-50">
														{#each sampleData?.columns || [] as col}
															<td class="px-2 py-1 text-slate-600 font-mono">
																{row[col] ?? 'NULL'}
															</td>
														{/each}
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
								</details>
							</div>
						{/if}
					{/if}
				</div>
			{/each}
		</div>

		<!-- Compact Legend -->
		<div class="bg-slate-100 rounded-lg p-2.5 border border-slate-200">
			<div class="flex items-center justify-between gap-4 text-xs">
				<span class="text-slate-600 font-medium">Legend:</span>
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-1.5">
						<svg class="w-2.5 h-2.5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M18 8a6 6 0 01-7.743 5.743L10 14l-1 1-1 1H6v2H2v-4l4.257-4.257A6 6 0 1118 8zm-6-4a1 1 0 100 2 2 2 0 012 2 1 1 0 102 0 4 4 0 00-4-4z" clip-rule="evenodd" />
						</svg>
						<span class="text-slate-700">PK</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg class="w-2.5 h-2.5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clip-rule="evenodd" />
						</svg>
						<span class="text-slate-700">FK</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg class="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
						</svg>
						<span class="text-slate-700">Click to select</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg class="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
						<span class="text-slate-700">Click table to expand</span>
					</div>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="text-center py-8 text-slate-500 text-sm">
		<svg class="w-12 h-12 mx-auto mb-2 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"
			/>
		</svg>
		Select a database to view schema
	</div>
{/if}
