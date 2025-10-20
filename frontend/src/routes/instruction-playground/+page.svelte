<script lang="ts">
	import { tick } from 'svelte';
	import { chatActions, currentMessage, customInstruction } from '$lib/stores/chat';
	import TemplateSelector from '$lib/components/TemplateSelector.svelte';
	import ChatContainer from '$lib/components/ChatContainer.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';

	let selectedTemplate = $state('funny');
	let showSettings = $state(false);
	let chatContainer = $state<ChatContainer>();

	async function handleSubmit() {
		await chatActions.sendInstructionMessage($currentMessage || '', $customInstruction);
		await tick();
		chatContainer?.scrollToBottom();
	}

	function handleInterrupt() {
		chatActions.interrupt();
	}
</script>

<svelte:head>
	<title>Instruction Playground</title>
</svelte:head>

<div class="max-w-4xl mx-auto h-[calc(100vh-200px)] flex flex-col">
	<div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-full">
		<TemplateSelector bind:selectedTemplate bind:customInstruction={$customInstruction} bind:showSettings />
		
		<ChatContainer bind:this={chatContainer} />
		
		<ChatInput onsubmit={handleSubmit} oninterrupt={handleInterrupt} />
	</div>
</div>