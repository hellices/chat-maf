<script lang="ts">
	import { tick, onMount } from 'svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import DatabaseERDiagram from '$lib/components/DatabaseERDiagram.svelte';

	let message = $state('');
	let messages = $state<Array<{ role: 'user' | 'assistant'; content: string; sql?: string; result?: any }>>([]);
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
						result: finalResult.execution_result
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
					<div class="text-center max-w-2xl">
						<div class="text-5xl mb-4">💬</div>
						<h3 class="text-xl font-semibold text-slate-900 mb-2">
							Welcome to NL2SQL Chat
						</h3>
						<p class="text-slate-600 mb-6">
							Ask questions about your database in natural language
						</p>
						<div class="flex flex-wrap gap-2 justify-center">
							{#each exampleQueries as query}
								<button
									onclick={() => useExample(query)}
									class="px-3 py-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
									disabled={isLoading}
								>
									{query}
								</button>
							{/each}
						</div>
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
			class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
			tabindex="-1"
		>
			<!-- Modal Header -->
			<div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white px-6 py-4 rounded-t-2xl">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="bg-white/20 backdrop-blur-sm p-2 rounded-lg">
							<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</div>
						<h2 id="modal-title" class="text-xl font-bold">About NL2SQL Playground</h2>
					</div>
					<button
						onclick={() => showInfoModal = false}
						class="hover:bg-white/20 rounded-lg p-1.5 transition-colors"
						aria-label="Close modal"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>

			<!-- Modal Content -->
			<div class="p-6 space-y-5">
				<!-- Introduction -->
				<div class="flex items-start gap-3">
					<div class="bg-blue-100 p-2 rounded-lg flex-shrink-0">
						<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="font-semibold text-slate-900 mb-1">What is this?</h3>
						<p class="text-slate-600 text-sm leading-relaxed">
							An interactive playground for experimenting with Natural Language to SQL (NL2SQL) conversion 
							using the <span class="font-semibold text-blue-600">Spider dataset</span>. Convert your questions 
							in natural language into executable SQL queries.
						</p>
					</div>
				</div>

				<!-- Spider Dataset -->
				<div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-200">
					<div class="flex items-start gap-3">
						<div class="bg-purple-500 p-2 rounded-lg flex-shrink-0">
							<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
							</svg>
						</div>
						<div class="flex-1">
							<h3 class="font-semibold text-purple-900 mb-1.5 flex items-center gap-2">
								Spider Dataset
								<a 
									href="https://github.com/taoyds/spider" 
									target="_blank" 
									rel="noopener noreferrer"
									class="inline-flex items-center gap-1 text-xs bg-purple-700 text-white px-2 py-0.5 rounded-full hover:bg-purple-800 transition-colors"
								>
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
										<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
									</svg>
									GitHub
								</a>
							</h3>
							<p class="text-purple-800 text-sm leading-relaxed">
								A large-scale text-to-SQL benchmark dataset with 200+ databases across diverse domains, 
								10,181 questions, and 5,693 complex SQL queries. Perfect for training and evaluating NL2SQL systems.
							</p>
						</div>
					</div>
				</div>

				<!-- How to Use - 2 columns layout -->
				<div>
					<div class="flex items-center gap-2 mb-3">
						<div class="bg-green-100 p-2 rounded-lg">
							<svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</div>
						<h3 class="font-semibold text-slate-900">How to Use</h3>
					</div>
					<div class="grid grid-cols-2 gap-4">
						<div class="flex items-start gap-2 text-sm text-slate-600">
							<span class="font-bold text-green-600 flex-shrink-0 bg-green-100 w-6 h-6 rounded-full flex items-center justify-center text-xs">1</span>
							<span><span class="font-semibold text-slate-900">Select a database</span> from the left sidebar (click again to deselect)</span>
						</div>
						<div class="flex items-start gap-2 text-sm text-slate-600">
							<span class="font-bold text-green-600 flex-shrink-0 bg-green-100 w-6 h-6 rounded-full flex items-center justify-center text-xs">2</span>
							<span><span class="font-semibold text-slate-900">Click tables</span> in the schema diagram to view columns and select specific tables</span>
						</div>
						<div class="flex items-start gap-2 text-sm text-slate-600">
							<span class="font-bold text-green-600 flex-shrink-0 bg-green-100 w-6 h-6 rounded-full flex items-center justify-center text-xs">3</span>
							<span><span class="font-semibold text-slate-900">Ask your question</span> in natural language - SQL will be generated automatically</span>
						</div>
						<div class="flex items-start gap-2 text-sm text-slate-600">
							<span class="font-bold text-green-600 flex-shrink-0 bg-green-100 w-6 h-6 rounded-full flex items-center justify-center text-xs">4</span>
							<span><span class="font-semibold text-slate-900">View results</span> with generated SQL query and execution results</span>
						</div>
					</div>
				</div>

				<!-- Features & Tips - Combined in 2 columns -->
				<div class="grid grid-cols-2 gap-4">
					<!-- Features -->
					<div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-4 border border-blue-200">
						<h3 class="font-semibold text-blue-900 mb-2.5 flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
							</svg>
							Key Features
						</h3>
						<div class="space-y-1.5 text-sm">
							<div class="flex items-center gap-2">
								<svg class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
								</svg>
								<span class="text-blue-800">ERD-style schema visualization</span>
							</div>
							<div class="flex items-center gap-2">
								<svg class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
								</svg>
								<span class="text-blue-800">Interactive table selection</span>
							</div>
							<div class="flex items-center gap-2">
								<svg class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
								</svg>
								<span class="text-blue-800">Real-time SQL generation</span>
							</div>
							<div class="flex items-center gap-2">
								<svg class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
								</svg>
								<span class="text-blue-800">Query execution & results</span>
							</div>
						</div>
					</div>

					<!-- Tips -->
					<div class="bg-amber-50 rounded-xl p-4 border border-amber-200">
						<h3 class="font-semibold text-amber-900 mb-2.5 flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
							</svg>
							💡 Pro Tips
						</h3>
						<ul class="space-y-1.5 text-sm text-amber-800">
							<li class="flex items-start gap-1.5">
								<span class="text-amber-600 flex-shrink-0">•</span>
								<span>Select specific tables for more accurate SQL generation</span>
							</li>
							<li class="flex items-start gap-1.5">
								<span class="text-amber-600 flex-shrink-0">•</span>
								<span>The AI focuses on selected tables, especially useful for complex databases</span>
							</li>
							<li class="flex items-start gap-1.5">
								<span class="text-amber-600 flex-shrink-0">•</span>
								<span>Try example queries to see how it works</span>
							</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- Modal Footer -->
			<div class="border-t border-slate-200 px-6 py-4 bg-slate-50 rounded-b-2xl">
				<button
					onclick={() => showInfoModal = false}
					class="w-full px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 text-white rounded-lg font-medium transition-all shadow-sm hover:shadow-md"
				>
					Got it! Let's start
				</button>
			</div>
		</div>
	</div>
{/if}
