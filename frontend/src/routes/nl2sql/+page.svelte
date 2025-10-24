<script lang="ts">
	import { onMount } from 'svelte';
	import { nl2sqlStore } from '$lib/stores/nl2sql';
	import { nl2sqlApi } from '$lib/services/nl2sql-api';
	import { getStepDisplay } from '$lib/config/workflow-steps';
	import { scrollToBottom } from '$lib/utils/helpers';
	
	import DatabaseERDiagram from '$lib/components/DatabaseERDiagram.svelte';
	import DatabaseSidebar from './components/DatabaseSidebar.svelte';
	import MessageBubble from './components/MessageBubble.svelte';
	import QueryInput from './components/QueryInput.svelte';
	import LoadingIndicator from './components/LoadingIndicator.svelte';
	import InfoModal from './components/InfoModal.svelte';
	import IterationSteps from './components/IterationSteps.svelte';

	let chatContainerEl: HTMLDivElement;

	// Subscribe to store
	const store = nl2sqlStore;

	onMount(async () => {
		store.clearStreamingLogs();
		await loadDatabases();
	});

	async function loadDatabases() {
		store.setLoadingDatabases(true);
		try {
			const databases = await nl2sqlApi.getDatabases();
			store.setDatabases(databases);
		} catch (e) {
			console.error('Failed to load databases:', e);
			store.setLoadingDatabases(false);
		}
	}

	async function handleSelectDatabase(dbName: string) {
		const currentDb = $store.selectedDatabase;
		
		if (currentDb === dbName) {
			store.setSelectedDatabase(null);
			store.setDatabaseSchema(null);
			return;
		}
		
		store.setSelectedDatabase(dbName);
		store.setLoadingSchema(true);
		
		try {
			const schema = await nl2sqlApi.getDatabaseRelationships(dbName);
			store.setDatabaseSchema(schema);
		} catch (e) {
			console.error('Failed to load schema:', e);
			store.setLoadingSchema(false);
		}
	}

	async function handleSubmit() {
		const message = $store.currentMessage.trim();
		if (!message || $store.isLoading) return;

		store.addMessage({
			role: 'user',
			content: message
		});
		
		store.setCurrentMessage('');
		store.setLoading(true, '');
		store.clearStreamingLogs();

		await scrollToBottom(chatContainerEl);

		try {
			let finalResult: any = null;

			for await (const event of nl2sqlApi.streamQuery({
				message,
				selected_database: $store.selectedDatabase,
				selected_tables: $store.selectedTables.length > 0 ? $store.selectedTables : undefined
			})) {
				if ('type' in event) {
					switch (event.type) {
					case 'WorkflowStatusEvent':
					case 'ExecutorInvokedEvent':
						if ('step_name' in event && event.step_name) {
							const stepDisplay = 'step_label' in event ? event.step_label : getStepDisplay(event.step_name);
							const stepCategory = 'step_category' in event ? event.step_category : undefined;
							store.setCurrentStep(stepDisplay);
								
							if (event.type === 'ExecutorInvokedEvent' && 'data' in event && event.data) {
								const content = typeof event.data === 'string' ? event.data.trim() : event.data;
								if (content && content !== '') {
									store.addStreamingLog(event.step_name, stepDisplay, content, stepCategory);
								}
							}
								
							await scrollToBottom(chatContainerEl);
						}
						break;

					case 'AgentRunUpdateEvent':
						if ('data' in event && event.data && 'step_name' in event && event.step_name) {
							const content = typeof event.data === 'string' ? event.data.trim() : event.data;
							if (content && content !== '') {
								const stepDisplay = 'step_label' in event ? event.step_label : getStepDisplay(event.step_name);
								const stepCategory = 'step_category' in event ? event.step_category : undefined;
								store.addStreamingLog(event.step_name, stepDisplay, content, stepCategory);
								store.setCurrentStep(stepDisplay);
								await scrollToBottom(chatContainerEl);
							}
						}
						break;

					case 'WorkflowOutputEvent':
						if ('data' in event) {
							finalResult = event.data;
						}
						break;

					case 'progress':
						if ('executor_id' in event && event.executor_id) {
							const stepDisplay = 'step_label' in event 
								? event.step_label 
								: getStepDisplay(event.executor_id, event.data?.summary);
							store.setCurrentStep(stepDisplay);
							await scrollToBottom(chatContainerEl);
						}
						break;
					}
				}

				if ('status' in event && event.status === 'error') {
					throw new Error(event.error || event.message || 'Unknown error');
				}

				if ('status' in event && event.status === 'completed') {
					break;
				}
			}

			if (finalResult) {
				console.log('Final Result:', finalResult);
				console.log('Reasoning Evaluation:', finalResult.reasoning_evaluation);
				
				store.addMessage({
					role: 'assistant',
					content: finalResult.natural_language_response || 'Query executed successfully.',
					sql: finalResult.sql,
					result: finalResult.execution_result,
					database: finalResult.database,
					reasoning_evaluation: finalResult.reasoning_evaluation
				});
				await scrollToBottom(chatContainerEl);
			}
		} catch (e: any) {
			console.error('Error:', e);
			store.addMessage({
				role: 'assistant',
				content: `❌ Error: ${e.message}`
			});
			await scrollToBottom(chatContainerEl);
		} finally {
			store.setLoading(false, '');
		}
	}
</script>

<svelte:head>
	<title>NL2SQL Chat</title>
</svelte:head>

<div class="flex flex-col h-[calc(100vh-128px)] overflow-hidden">
	<div class="flex gap-4 flex-1 min-h-0 p-4 pb-0">
		<!-- Sidebar -->
		{#if $store.showSidebar}
			<DatabaseSidebar
				databases={$store.databases}
				selectedDatabase={$store.selectedDatabase}
				loading={$store.loadingDatabases}
				onSelectDatabase={handleSelectDatabase}
				onClose={() => store.setSidebarVisible(false)}
			/>
		{/if}

		<!-- Main Chat Area -->
		<div class="flex-1 flex flex-col min-w-0">
			{#if !$store.showSidebar}
				<button
					onclick={() => store.setSidebarVisible(true)}
					class="mb-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm transition-colors self-start flex items-center gap-2"
					aria-label="Show database sidebar"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
					</svg>
					Show Databases
				</button>
			{/if}

			<div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col flex-1 min-h-0">
				<!-- Header -->
				<div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
					<div>
						<h2 class="text-lg font-semibold text-slate-900">NL2SQL Chat</h2>
						<p class="text-sm text-slate-600">
							{$store.selectedDatabase 
								? `Connected to: ${$store.selectedDatabase}` 
								: 'Ask questions in natural language and get SQL results'}
						</p>
						{#if $store.selectedTables.length > 0}
							<div class="flex items-center gap-1 mt-1">
								<span class="text-xs text-slate-500">Using tables:</span>
								{#each $store.selectedTables as table}
									<span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
										{table}
									</span>
								{/each}
							</div>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						{#if $store.selectedDatabase}
							<span class="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
								● {$store.selectedDatabase}
							</span>
						{/if}
						<button
							onclick={() => store.toggleInfoModal()}
							class="p-2 hover:bg-slate-100 rounded-lg transition-colors"
							title="About this playground"
							aria-label="Show information modal"
						>
							<svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</button>
					</div>
				</div>

				<!-- Chat Messages -->
				<div 
					bind:this={chatContainerEl} 
					class="flex-1 overflow-y-auto px-6 py-4 space-y-6"
					role="log"
					aria-live="polite"
					aria-label="Chat messages"
				>
					{#if $store.messages.length === 0}
						<!-- Welcome Message -->
						<div class="flex items-center justify-center h-full">
							<div class="text-center max-w-xl">
								<div class="text-5xl mb-4" aria-hidden="true">💬</div>
								<h3 class="text-xl font-semibold text-slate-900 mb-3">
									Welcome to NL2SQL Chat
								</h3>
								<p class="text-slate-600 mb-6">
									Ask questions about your database in natural language
								</p>
								<button
									onclick={() => store.toggleInfoModal()}
									class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors text-sm font-medium"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Click here to learn how to use
								</button>
							</div>
						</div>
					{:else}
						{#each $store.messages as msg, index (msg.id || `msg-${msg.role}-${msg.content.substring(0, 20)}`)}
							{#if !(msg.role === 'assistant' && index === $store.messages.length - 1 && $store.streamingLogs.length > 0)}
								<MessageBubble message={msg} />
							{/if}
						{/each}

						{#if $store.streamingLogs.length > 0}
							<IterationSteps 
								logs={$store.streamingLogs} 
								onToggle={(id) => store.toggleStreamingLog(id)}
							/>
						{/if}

						{#if $store.streamingLogs.length > 0 && $store.messages.length > 0}
							{@const lastMsg = $store.messages[$store.messages.length - 1]}
							{#if lastMsg.role === 'assistant'}
								<div class="mt-4 pt-4 border-t-2 border-blue-200">
									<div class="text-xs font-semibold text-blue-600 mb-2 uppercase tracking-wide">MAF Agent</div>
									<MessageBubble message={lastMsg} />
								</div>
							{/if}
						{/if}

						{#if $store.isLoading}
							<LoadingIndicator currentStep={$store.currentStep} />
						{/if}
					{/if}
				</div>

				<QueryInput
					message={$store.currentMessage}
					isLoading={$store.isLoading}
					onSubmit={handleSubmit}
					onMessageChange={(value) => store.setCurrentMessage(value)}
				/>
			</div>
		</div>
	</div>
	
	{#if $store.selectedDatabase && $store.databaseSchema}
		<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mx-4 mb-4 flex-shrink-0 overflow-y-auto" style="max-height: 35vh;">
			{#if $store.loadingSchema}
				<div class="text-center py-8 text-slate-500 text-sm" role="status" aria-live="polite">
					<svg class="animate-spin h-5 w-5 mx-auto mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Loading schema...
				</div>
			{:else}
				<DatabaseERDiagram 
					bind:schema={$store.databaseSchema} 
					bind:selectedTables={$store.selectedTables}
					onTableClick={(tableName) => store.toggleTableSelection(tableName)}
				/>
			{/if}
		</div>
	{/if}
</div>

<InfoModal
	show={$store.showInfoModal}
	onClose={() => store.setInfoModalVisible(false)}
/>
