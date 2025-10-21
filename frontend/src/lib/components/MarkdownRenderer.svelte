<script lang="ts">
	import { marked } from 'marked';
	import { onMount } from 'svelte';

	let { content = '' }: { content: string } = $props();
	let htmlContent = $state('');

	// Configure marked for better formatting
	marked.setOptions({
		gfm: true, // GitHub Flavored Markdown
		breaks: true, // Convert \n to <br>
	});

	// Convert markdown to HTML
	$effect(() => {
		if (content) {
			const result = marked.parse(content);
			if (typeof result === 'string') {
				htmlContent = result;
			} else {
				result.then((html: string) => {
					htmlContent = html;
				});
			}
		}
	});
</script>

<div class="markdown-content prose prose-slate max-w-none">
	{@html htmlContent}
</div>

<style>
	.markdown-content {
		line-height: 1.6;
	}

	/* Headings */
	.markdown-content :global(h1) {
		font-size: 1.5rem;
		font-weight: 700;
		margin-top: 1rem;
		margin-bottom: 0.5rem;
		color: #1e293b;
	}

	.markdown-content :global(h2) {
		font-size: 1.25rem;
		font-weight: 600;
		margin-top: 0.75rem;
		margin-bottom: 0.5rem;
		color: #334155;
	}

	.markdown-content :global(h3) {
		font-size: 1.125rem;
		font-weight: 600;
		margin-top: 0.5rem;
		margin-bottom: 0.25rem;
		color: #475569;
	}

	/* Paragraphs */
	.markdown-content :global(p) {
		margin-bottom: 0.75rem;
		color: #334155;
	}

	/* Bold */
	.markdown-content :global(strong) {
		font-weight: 600;
		color: #1e293b;
	}

	/* Italic */
	.markdown-content :global(em) {
		font-style: italic;
		color: #475569;
	}

	/* Lists */
	.markdown-content :global(ul) {
		list-style-type: disc;
		padding-left: 1.5rem;
		margin-bottom: 0.75rem;
	}

	.markdown-content :global(ol) {
		list-style-type: decimal;
		padding-left: 1.5rem;
		margin-bottom: 0.75rem;
	}

	.markdown-content :global(li) {
		margin-bottom: 0.25rem;
		color: #334155;
	}

	/* Code */
	.markdown-content :global(code) {
		background-color: #f1f5f9;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-family: 'Courier New', monospace;
		color: #dc2626;
	}

	.markdown-content :global(pre) {
		background-color: #1e293b;
		color: #e2e8f0;
		padding: 0.75rem;
		border-radius: 0.5rem;
		overflow-x: auto;
		margin-bottom: 0.75rem;
	}

	.markdown-content :global(pre code) {
		background-color: transparent;
		padding: 0;
		color: #e2e8f0;
		font-size: 0.875rem;
	}

	/* Tables */
	.markdown-content :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin-bottom: 0.75rem;
		font-size: 0.875rem;
	}

	.markdown-content :global(th) {
		background-color: #f1f5f9;
		border: 1px solid #cbd5e1;
		padding: 0.5rem;
		text-align: left;
		font-weight: 600;
		color: #1e293b;
	}

	.markdown-content :global(td) {
		border: 1px solid #e2e8f0;
		padding: 0.5rem;
		color: #334155;
	}

	.markdown-content :global(tr:hover) {
		background-color: #f8fafc;
	}

	/* Blockquotes */
	.markdown-content :global(blockquote) {
		border-left: 4px solid #cbd5e1;
		padding-left: 1rem;
		margin-left: 0;
		margin-bottom: 0.75rem;
		color: #64748b;
		font-style: italic;
	}

	/* Links */
	.markdown-content :global(a) {
		color: #2563eb;
		text-decoration: underline;
	}

	.markdown-content :global(a:hover) {
		color: #1d4ed8;
	}

	/* Horizontal Rule */
	.markdown-content :global(hr) {
		border: none;
		border-top: 1px solid #e2e8f0;
		margin: 1rem 0;
	}
</style>
