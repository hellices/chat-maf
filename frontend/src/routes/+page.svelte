<script lang="ts">
	let routes = $state<Array<{path: string, name: string, description: string}>>([]);

	$effect(() => {
		async function loadRoutes() {
			const modules = import.meta.glob('./**/+page.svelte');
			const routePaths = Object.keys(modules);
			
			routes = routePaths
				.map(path => {
					const routePath = path
						.replace('./+page.svelte', '/')
						.replace('./+page.svelte', '/')
						.replace(/\/\+page\.svelte$/, '')
						.replace(/^\./, '') || '/';
					
					let name = '';
					let description = '';
					
					if (routePath === '/') {
						name = 'Home';
						description = 'The main landing page';
					} else if (routePath === '/instruction-playground') {
						name = 'Instruction Playground';
						description = 'Test different AI instructions and behaviors';
					} else if (routePath === '/website-assistant') {
						name = 'Website Assistant';
						description = 'Interactive website analysis with iframe and chat';
					} else {
						name = routePath
							.split('/')
							.filter(Boolean)
							.map(segment => segment.charAt(0).toUpperCase() + segment.slice(1))
							.join(' ');
						description = `${name} page`;
					}
					
					return { path: routePath, name, description };
				})
				.sort((a, b) => a.path.localeCompare(b.path));
		}

		loadRoutes();
	});
</script>

<div class="space-y-8">
	<!-- Hero Section -->
	<div class="text-center">
		<h1 class="text-4xl font-bold text-gray-900 mb-4">
			Svelte & Microsoft Agent Framework Demo
		</h1>
	</div>

	<!-- Routes List -->
	<div class="bg-white rounded-lg shadow-md p-6 border border-gray-200">
		<h2 class="text-xl font-semibold text-gray-900 mb-4">Available Routes</h2>
		<div class="space-y-3">
			{#each routes as route (route.path)}
				<a 
					href={route.path}
					class="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200"
				>
					<div class="flex items-center">
						<svg class="w-5 h-5 text-blue-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							{#if route.path === '/'}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z" />
							{:else}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
							{/if}
						</svg>
						<div>
							<div class="font-medium text-gray-900">{route.path}</div>
							<div class="text-sm text-gray-600">{route.description}</div>
						</div>
					</div>
					<svg class="w-4 h-4 ml-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			{/each}
		</div>
	</div>
</div>
