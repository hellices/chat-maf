<script lang="ts">
import type { StreamingLog } from '$lib/stores/nl2sql';

interface Props {
logs: StreamingLog[];
onToggle: (id: string) => void;
}

let { logs, onToggle }: Props = $props();

let expandedGroups = $state<Set<string>>(new Set(['schema', 'sql']));

interface StepGroup {
type: 'schema' | 'sql';
label: string;
logs: StreamingLog[];
isExpanded: boolean;
}

const groupedSteps = $derived.by(() => {
	const groups: StepGroup[] = [];
	const schemaLogs: StreamingLog[] = [];
	const sqlLogs: StreamingLog[] = [];

	const validLogs = logs
		.filter(log => log && (log.id || log.stepName))
		.map(log => {
			if (!log.id) {
				return {
					...log,
					id: `${log.stepName}-${log.timestamp || Date.now()}-${Math.random().toString(36).substr(2, 9)}`
				};
			}
			return log;
		});

	validLogs.forEach((log) => {
		const category = log.stepCategory || '';
		const isSchemaStep = 
			category === 'schema' || 
			category === 'initialization' ||
			log.stepName.includes('schema') || 
			log.stepName.includes('understand') ||
			log.stepName.includes('analyze');

		const isSqlStep = 
			category === 'sql' ||
			log.stepName.includes('sql') || 
			log.stepName.includes('generate') ||
			log.stepName.includes('parse');

		if (isSchemaStep) {
			schemaLogs.push(log);
		} else if (isSqlStep) {
			sqlLogs.push(log);
		}
		});

	if (schemaLogs.length > 0) {
		groups.push({
			type: 'schema',
			label: `Schema Analysis (${schemaLogs.length})`,
			logs: schemaLogs,
			isExpanded: expandedGroups.has('schema')
		});
	}

	if (sqlLogs.length > 0) {
		groups.push({
			type: 'sql',
			label: `SQL Generation (${sqlLogs.length})`,
			logs: sqlLogs,
			isExpanded: expandedGroups.has('sql')
		});
	}

	return groups;
});

function toggleGroup(groupType: string) {
	if (expandedGroups.has(groupType)) {
		expandedGroups.delete(groupType);
	} else {
		expandedGroups.add(groupType);
	}
	expandedGroups = expandedGroups;
}

function getStatusFromContent(content: string): 'success' | 'warning' | 'error' {
	try {
		const parsed = JSON.parse(content);
		if (parsed.confidence !== undefined) {
			if (parsed.confidence === 0 || parsed.sql === '') return 'error';
			if (parsed.confidence < 50) return 'warning';
			return 'success';
		}
		if (parsed.tables !== undefined) {
			if (Array.isArray(parsed.tables) && parsed.tables.length === 0) return 'error';
			return 'success';
		}
	} catch (e) {}
	return 'success';
}

function getStatusIcon(status: string) {
	return status === 'success' ? '✅' : status === 'warning' ? '⚠️' : '❌';
}

function getStatusColor(status: string) {
	return status === 'success' 
		? 'text-green-600 dark:text-green-400'
		: status === 'warning'
		? 'text-yellow-600 dark:text-yellow-400'
		: 'text-red-600 dark:text-red-400';
}

function getSummary(log: StreamingLog): string {
	try {
		const content = JSON.parse(log.content);

		if (content.database && content.tables !== undefined) {
			const tableCount = Array.isArray(content.tables) ? content.tables.length : 0;
			if (tableCount === 0) return `Database: ${content.database} → No tables selected`;
			return `Database: ${content.database} → Tables: ${content.tables.join(', ')}`;
		}

		if (content.sql !== undefined) {
			const confidence = content.confidence || 0;
			if (confidence === 0 || content.sql === '') return 'No query generated';
			const preview = content.sql.substring(0, 60).replace(/\s+/g, ' ');
			return `${preview}... (Confidence: ${confidence}%)`;
		}
	} catch (e) {}
	return log.content.substring(0, 60);
}
</script>

{#if groupedSteps.length > 0}
	<div class="iteration-steps space-y-3 my-4">
		{#each groupedSteps as group (group.type)}
			<div class="step-group border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
				<button
					class="group-header w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 hover:from-blue-100 hover:to-indigo-100 dark:hover:from-blue-900/30 dark:hover:to-indigo-900/30 transition-colors"
					onclick={() => toggleGroup(group.type)}
				>
					<div class="flex items-center gap-3">
						<span class="text-blue-600 dark:text-blue-400">
							{#if group.isExpanded}
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="6 9 12 15 18 9"></polyline>
								</svg>
							{:else}
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="9 18 15 12 9 6"></polyline>
								</svg>
							{/if}
						</span>
						<span class="font-semibold text-gray-900 dark:text-gray-100">
							{group.label}
						</span>
					</div>
					<div class="flex items-center gap-2">
						{#each group.logs as log (log.id)}
							<span class="text-lg">
								{getStatusIcon(getStatusFromContent(log.content))}
							</span>
						{/each}
					</div>
				</button>

				{#if group.isExpanded}
					<div class="logs-list divide-y divide-gray-200 dark:divide-gray-700">
						{#each group.logs as log, index (log.id)}
							<div class="log-item">
								<button
									class="w-full px-4 py-2.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
									onclick={() => onToggle(log.id)}
								>
									<div class="flex items-center gap-3 flex-1 min-w-0">
										<span class={`text-lg ${getStatusColor(getStatusFromContent(log.content))}`}>
											{getStatusIcon(getStatusFromContent(log.content))}
										</span>
										<div class="flex flex-col items-start flex-1 min-w-0">
											<span class="text-sm text-gray-700 dark:text-gray-300 text-left truncate w-full">
												{getSummary(log)}
											</span>
										</div>
									</div>
									<span class="text-blue-600 dark:text-blue-400 flex-shrink-0">
										{#if log.isExpanded}
											<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<polyline points="6 9 12 15 18 9"></polyline>
											</svg>
										{:else}
											<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<polyline points="9 18 15 12 9 6"></polyline>
											</svg>
										{/if}
									</span>
								</button>

								{#if log.isExpanded}
									<div class="log-content p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
										<pre class="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words font-mono overflow-x-auto">{log.content}</pre>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}

<style>
.iteration-steps {
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

.group-header,
.log-item button {
cursor: pointer;
user-select: none;
}

pre {
max-height: 300px;
overflow-y: auto;
}
</style>
