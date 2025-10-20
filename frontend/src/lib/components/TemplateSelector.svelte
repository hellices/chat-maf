<script lang="ts">
	interface Props {
		selectedTemplate: string;
		customInstruction?: string;
		showSettings?: boolean;
	}

	let { selectedTemplate = $bindable(), customInstruction = $bindable(''), showSettings = $bindable(false) }: Props = $props();

	const templates = [
		{ 
			value: 'helpful', 
			label: 'Helpful Assistant',
			instruction: 'You are a helpful AI assistant that provides accurate and useful information.'
		},
		{ 
			value: 'funny', 
			label: 'Funny Bot',
			instruction: 'You are a funny bot that tells jokes and makes people laugh.'
		},
		{ 
			value: 'code_reviewer', 
			label: 'Code Reviewer',
			instruction: 'You are a code reviewer that provides constructive feedback on code quality, best practices, and potential improvements.'
		},
		{ 
			value: 'translator', 
			label: 'Translator',
			instruction: 'You are a professional translator that can translate text between different languages accurately.'
		},
		{ 
			value: 'scientist', 
			label: 'Scientific Expert',
			instruction: 'You are a scientific researcher and expert who explains complex scientific concepts clearly, provides evidence-based answers, and discusses the latest research findings across various scientific disciplines.'
		},
		{ 
			value: 'historian', 
			label: 'Professional Historian',
			instruction: 'You are a professional historian with deep knowledge of world history. You provide accurate historical context, analyze historical events and their causes, and explain how past events connect to present circumstances.'
		},
		{ 
			value: 'philosopher', 
			label: 'Philosopher',
			instruction: 'You are a philosopher who explores deep questions about existence, ethics, knowledge, and meaning. You engage in thoughtful analysis of complex ideas and help examine different perspectives on fundamental questions.'
		},
		{ 
			value: 'custom', 
			label: 'Custom Instruction',
			instruction: ''
		}
	];

	function onTemplateChange() {
		const selected = templates.find(t => t.value === selectedTemplate);
		if (selected && selected.value !== 'custom') {
			customInstruction = selected.instruction;
		} else if (selected && selected.value === 'custom') {
			customInstruction = '';
		}
	}

	$effect(() => {
		if (selectedTemplate) {
			onTemplateChange();
		}
	});
</script>

<div class="p-6 border-b border-slate-100">
	<div class="flex justify-between items-center">
		<div>
			<h1 class="text-xl font-medium text-slate-800">Chat Stream</h1>
			<p class="text-sm text-slate-500">Real-time chat with AI agent</p>
		</div>
		<button
			onclick={() => showSettings = !showSettings}
			class="p-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600"
			aria-label="Settings"
		>
			<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
			</svg>
		</button>
	</div>
	
	{#if showSettings}
		<div class="mt-4 space-y-4 p-4 bg-slate-50 rounded-xl">
			<div>
				<label for="template-select" class="block text-sm font-medium text-slate-700 mb-2">Template</label>
				<select 
					id="template-select"
					bind:value={selectedTemplate}
					onchange={onTemplateChange}
					class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-300"
				>
					{#each templates as template}
						<option value={template.value}>{template.label}</option>
					{/each}
				</select>
			</div>
			
			<div>
				<label for="instruction-textarea" class="block text-sm font-medium text-slate-700 mb-2">System Instruction</label>
				<textarea
					id="instruction-textarea"
					bind:value={customInstruction}
					placeholder="Define how the AI should behave and respond..."
					class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-300 resize-none"
					rows="4"
				></textarea>
				<p class="text-xs text-slate-500 mt-1">
					{selectedTemplate === 'custom' 
						? 'Enter your custom instruction' 
						: 'Template instruction loaded - you can modify it'}
				</p>
			</div>
		</div>
	{/if}
</div>