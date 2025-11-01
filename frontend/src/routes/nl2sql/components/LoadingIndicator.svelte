<script lang="ts">
	interface Props {
		currentStep: string;
	}

	let { currentStep }: Props = $props();
</script>

{#if currentStep}
	<div class="flex justify-start" role="status" aria-live="polite" aria-label="Processing step">
		<div class="bg-slate-100 text-slate-600 rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-sm">
			<div class="flex items-center gap-2 text-sm">
				<div class="flex gap-1" aria-hidden="true">
					<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
					<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
					<div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
				</div>
				<span class="text-[13px]">{currentStep}</span>
			</div>
		</div>
	</div>
{/if}
