<script lang="ts">
	import { tick } from 'svelte';
	import { chatActions, currentMessage, customInstruction } from '$lib/stores/chat';
	import ChatContainer from '$lib/components/ChatContainer.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';
	
	let iframeUrl = $state('https://www.microsoft.com/ko-kr/');
	let inputUrl = $state('https://www.microsoft.com/ko-kr/');
	let showChat = $state(false);
	let iframeElement: HTMLIFrameElement;
	let chatContainer = $state<ChatContainer>();
	
	function loadIframe() {
		if (inputUrl.trim()) {
			if (!inputUrl.startsWith('http://') && !inputUrl.startsWith('https://')) {
				inputUrl = 'https://' + inputUrl;
			}
			iframeUrl = inputUrl;
		}
	}
	
	function toggleChat() {
		showChat = !showChat;
	}
	
	async function handleSubmit() {
		// Send URL directly to backend for analysis
		await chatActions.sendWebsiteAssistantMessage($currentMessage || '', iframeUrl);
		await tick();
		chatContainer?.scrollToBottom();
	}

	function handleInterrupt() {
		chatActions.interrupt();
	}
	
	$effect(() => {
		function handleKeyDown(event: KeyboardEvent) {
			if ((event.ctrlKey || event.metaKey) && event.key === '`') {
				event.preventDefault();
				toggleChat();
			}
		}
		
		window.addEventListener('keydown', handleKeyDown);
		
		return () => {
			window.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<svelte:head>
	<title>Website Assistant - Interactive Website Analysis</title>
</svelte:head>

<div class="h-screen flex flex-col bg-gray-100">
	<div class="bg-white shadow-sm border-b border-gray-200 p-4 flex-shrink-0">
		<div class="max-w-4xl mx-auto flex gap-4 items-center">
			<label for="url-input" class="text-sm font-medium text-gray-700 flex-shrink-0">
				Website URL:
			</label>
			<input
				id="url-input"
				type="url"
				bind:value={inputUrl}
				placeholder="Try: https://example.com, https://httpbin.org, or other sites"
				class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				onkeydown={(e) => e.key === 'Enter' && loadIframe()}
			/>
			<button
				onclick={loadIframe}
				class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
			>
				Load
			</button>
			<button
				onclick={toggleChat}
				class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
				title="Toggle Chat (Ctrl/Cmd + `)"
			>
				{showChat ? 'Hide' : 'Chat'}
			</button>
		</div>
	</div>

	<div class="flex-1 relative overflow-hidden">
		<iframe
			bind:this={iframeElement}
			src={iframeUrl}
			title="External Website"
			class="w-full h-[calc(100vh-9rem)] border-0"
			sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation"
			style="min-width: 1200px;"
		></iframe>
		
		{#if showChat}
			<div class="fixed bottom-4 left-4 w-[28rem] h-[32rem] bg-white rounded-xl shadow-2xl border border-slate-200 flex flex-col z-50 max-h-[calc(100vh-2rem)]">
				<div class="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
					<div>
						<h3 class="font-semibold text-slate-800 text-sm">Website Assistant</h3>
						<p class="text-xs text-slate-500">Analyzing: {new URL(iframeUrl).hostname}</p>
					</div>
					<button
						onclick={toggleChat}
						class="text-slate-500 hover:text-slate-700 p-1 rounded"
						title="Close Chat"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				<ChatContainer bind:this={chatContainer} />
				<ChatInput onsubmit={handleSubmit} oninterrupt={handleInterrupt} />
			</div>
		{/if}
		
		{#if !showChat}
			<button
				onclick={toggleChat}
				class="fixed bottom-4 left-4 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-110 z-50"
				title="Open Chat (Ctrl/Cmd + `)"
			>
				<svg class="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
				</svg>
			</button>
		{/if}
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
	}
	
	iframe {
		transform-origin: 0 0;
		width: 100% !important;
		min-width: 1200px;
	}
	
	@media (max-width: 1200px) {
		iframe {
			transform: scale(0.8);
			width: 125% !important;
			height: calc(125% - 7.5rem) !important;
		}
	}
</style>