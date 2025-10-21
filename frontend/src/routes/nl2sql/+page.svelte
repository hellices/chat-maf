<script lang="ts">
	import { tick, onMount } from 'svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import DatabaseERDiagram from '$lib/components/DatabaseERDiagram.svelte';

	let message = $state('');
	let messages = $state<Array<{ role: 'user' | 'assistant'; content: string; sql?: string; result?: any; database?: string }>>([]);
	let isLoading = $state(false);
	let currentStep = $state('');
	let chatContainerEl: HTMLDivElement;

	// Spider database browser
	let databases = $state<string[]>([]);
	let selectedDatabase = $state<string | null>(null);
	let selectedTables = $state<string[]>([]); // 선택된 테이블 목록
	let databaseSchema = $state<any>(null);
	let loadingDatabases = $state(false);
	let showSidebar = $state(true);
	let loadingSchema = $state(false);
	let showInfoModal = $state(false);

	const stepNames: Record<string, string> = {
		initialize_workflow: '🔄 Initializing...',
		extract_entities: '🔍 Extracting entities...',
		map_schema: '🗺️ Mapping schema...',
		generate_sql: '⚡ Generating SQL...',
		execute_sql: '▶️ Executing query...',
		generate_nl_response: '💬 Formatting response...'
	};

	const exampleQueries = [
		'How many singers do we have?',
		'List all singer names',
		'What are the stadium names and their capacity?',
		'What is the average age of singers?'
	];

	onMount(async () => {
		await loadDatabases();
	});

	async function loadDatabases() {
		loadingDatabases = true;
		try {
			const response = await fetch('http://localhost:8000/spider/databases');
			databases = await response.json();
		} catch (e) {
			console.error('Failed to load databases:', e);
		} finally {
			loadingDatabases = false;
		}
	}

	async function selectDatabase(dbName: string) {
		// 이미 선택된 데이터베이스를 다시 클릭하면 선택 해제
		if (selectedDatabase === dbName) {
			selectedDatabase = null;
			selectedTables = [];
			databaseSchema = null;
			return;
		}
		
		selectedDatabase = dbName;
		selectedTables = []; // 데이터베이스 변경 시 선택된 테이블 초기화
		loadingSchema = true;
		try {
			const response = await fetch(`http://localhost:8000/spider/databases/${dbName}/relationships`);
			const data = await response.json();
			databaseSchema = data;
		} catch (e) {
			console.error('Failed to load schema:', e);
		} finally {
			loadingSchema = false;
		}
	}

	function toggleTableSelection(tableName: string) {
		const index = selectedTables.indexOf(tableName);
		if (index > -1) {
			// 이미 선택된 경우 - 선택 해제
			selectedTables = selectedTables.filter(t => t !== tableName);
		} else {
			// 선택되지 않은 경우 - 선택 추가
			selectedTables = [...selectedTables, tableName];
		}
	}

	async function scrollToBottom() {
		await tick();
		if (chatContainerEl) {
			chatContainerEl.scrollTop = chatContainerEl.scrollHeight;
		}
	}

	async function handleSubmit() {
		if (!message.trim() || isLoading) return;

		const userMessage = message;
		messages = [...messages, { role: 'user', content: userMessage }];
		message = '';
		isLoading = true;
		currentStep = '';

		await scrollToBottom();

		try {
			const response = await fetch('http://localhost:8000/nl2sql', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ 
					message: userMessage,
					selected_database: selectedDatabase,
					selected_tables: selectedTables.length > 0 ? selectedTables : undefined
				})
			});

			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			if (!reader) throw new Error('No reader available');

			let finalResult: any = null;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value);
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						try {
							const eventData = JSON.parse(line.substring(6));

							if (eventData.status === 'completed') {
								currentStep = '';
								break;
							}

							if (eventData.status === 'error') {
								throw new Error(eventData.error);
							}

							if (eventData.executor_id && stepNames[eventData.executor_id]) {
								currentStep = stepNames[eventData.executor_id];
								await scrollToBottom();
							}

							if (eventData.type === 'WorkflowOutputEvent' && eventData.data) {
								finalResult = eventData.data;
							}
						} catch (e) {
							console.error('Parse error:', e);
						}
					}
				}
			}

			if (finalResult) {
				messages = [
					...messages,
					{
						role: 'assistant',
						content: finalResult.natural_language_response || 'Query executed successfully.',
						sql: finalResult.sql,
						result: finalResult.execution_result,
						database: finalResult.database
					}
				];
				await scrollToBottom();
			}
		} catch (e: any) {
			console.error('Error:', e);
			messages = [...messages, { role: 'assistant', content: `❌ Error: ${e.message}` }];
			await scrollToBottom();
		} finally {
			isLoading = false;
			currentStep = '';
		}
	}

	function handleKeyPress(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}

	function useExample(query: string) {
		message = query;
	}
</script>

<svelte:head>
	<title>NL2SQL Chat</title>
</svelte:head>

<div class="flex flex-col h-[calc(100vh-128px)] overflow-hidden">
	<div class="flex gap-4 flex-1 min-h-0 p-4 pb-0">
	<!-- Sidebar - Database Browser -->
	{#if showSidebar}
		<div class="w-64 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
			<!-- Sidebar Header -->
			<div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
				<h3 class="font-semibold text-slate-900">📊 Databases</h3>
				<button
					onclick={() => showSidebar = false}
					class="text-slate-400 hover:text-slate-600 transition-colors"
					title="Hide sidebar"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</button>
			</div>

			<!-- Database List -->
			<div class="flex-1 overflow-y-auto p-3">
				{#if loadingDatabases}
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
								onclick={() => selectDatabase(db)}
								class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors {selectedDatabase === db ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-slate-100 text-slate-700'}"
							>
								{db}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Main Chat Area -->
	<div class="flex-1 flex flex-col min-w-0">
		{#if !showSidebar}
			<button
				onclick={() => showSidebar = true}
				class="mb-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm transition-colors self-start flex items-center gap-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
					{selectedDatabase ? `Connected to: ${selectedDatabase}` : 'Ask questions in natural language and get SQL results'}
				</p>
				{#if selectedTables.length > 0}
					<div class="flex items-center gap-1 mt-1">
						<span class="text-xs text-slate-500">Using tables:</span>
						{#each selectedTables as table}
							<span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
								{table}
							</span>
						{/each}
					</div>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				{#if selectedDatabase}
					<span class="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
						● {selectedDatabase}
					</span>
				{/if}
				<button
					onclick={() => showInfoModal = true}
					class="p-2 hover:bg-slate-100 rounded-lg transition-colors"
					title="About this playground"
				>
					<svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Chat Messages -->
		<div bind:this={chatContainerEl} class="flex-1 overflow-y-auto px-6 py-4 space-y-6">
			{#if messages.length === 0}
				<!-- Welcome Message -->
				<div class="flex items-center justify-center h-full">
					<div class="text-center max-w-xl">
						<div class="text-5xl mb-4">💬</div>
						<h3 class="text-xl font-semibold text-slate-900 mb-3">
							Welcome to NL2SQL Chat
						</h3>
						<p class="text-slate-600 mb-6">
							Ask questions about your database in natural language
						</p>
						<button
							onclick={() => showInfoModal = true}
							class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors text-sm font-medium"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Click here to learn how to use
						</button>
					</div>
				</div>
			{:else}
				<!-- Messages -->
				{#each messages as msg}
					{#if msg.role === 'user'}
						<div class="flex justify-end">
							<div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] shadow-sm">
								<p class="text-[15px] leading-relaxed">{msg.content}</p>
							</div>
						</div>
					{:else}
						<div class="flex justify-start">
							<div class="bg-slate-100 text-slate-900 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%] shadow-sm">
								<div class="text-[15px] leading-relaxed">
									<MarkdownRenderer content={msg.content} />
								</div>
								
								{#if msg.database}
									<div class="mt-2 text-xs text-slate-500 flex items-center gap-1">
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
										</svg>
										<span>Database: <span class="font-medium text-slate-700">{msg.database}</span></span>
									</div>
								{/if}
								
								{#if msg.sql}
									<details class="mt-3 group">
										<summary class="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1.5">
											<svg class="w-3 h-3 transform group-open:rotate-90 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
											</svg>
											SQL Query
										</summary>
										<pre class="mt-2 text-xs bg-slate-900 text-green-400 p-3 rounded-lg overflow-x-auto"><code>{msg.sql}</code></pre>
									</details>
								{/if}

								{#if msg.result}
									<details class="mt-2 group">
										<summary class="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1.5">
											<svg class="w-3 h-3 transform group-open:rotate-90 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
											</svg>
											Results
										</summary>
										<pre class="mt-2 text-xs bg-slate-900 text-slate-300 p-3 rounded-lg overflow-x-auto">{JSON.stringify(msg.result, null, 2)}</pre>
									</details>
								{/if}
							</div>
						</div>
					{/if}
				{/each}

				<!-- Loading Indicator -->
				{#if isLoading && currentStep}
					<div class="flex justify-start">
						<div class="bg-slate-100 text-slate-600 rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-sm">
							<div class="flex items-center gap-2 text-sm">
								<div class="flex gap-1">
									<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
									<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
									<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
								</div>
								<span class="text-[13px]">{currentStep}</span>
							</div>
						</div>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Input Area -->
		<div class="border-t border-slate-200 p-4">
			<div class="flex gap-2">
				<textarea
					bind:value={message}
					onkeypress={handleKeyPress}
					placeholder="Ask a question about your database..."
					class="flex-1 resize-none rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					rows="1"
					disabled={isLoading}
				></textarea>
				<button
					onclick={handleSubmit}
					disabled={isLoading || !message.trim()}
					class="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
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
		</div>
	</div>
	</div>
	
	<!-- Schema Diagram - Full Width Bottom Section -->
	{#if selectedDatabase && databaseSchema}
		<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mx-4 mb-4 flex-shrink-0 overflow-y-auto" style="max-height: 35vh;">
			{#if loadingSchema}
				<div class="text-center py-8 text-slate-500 text-sm">
					<svg class="animate-spin h-5 w-5 mx-auto mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Loading schema...
				</div>
			{:else}
				<DatabaseERDiagram 
					bind:schema={databaseSchema} 
					bind:selectedTables={selectedTables}
					onTableClick={toggleTableSelection}
				/>
			{/if}
		</div>
	{/if}
</div>

<!-- Info Modal -->
{#if showInfoModal}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div 
		class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
		onclick={() => showInfoModal = false}
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
						onclick={() => showInfoModal = false}
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
					onclick={() => showInfoModal = false}
					class="w-full px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-medium transition-colors"
				>
					Got it
				</button>
			</div>
		</div>
	</div>
{/if}
