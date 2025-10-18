<script lang="ts">
	import { page } from '$app/stores';
</script>

<header class="bg-white shadow-sm border-b border-gray-200">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="flex justify-between items-center h-16">
			<!-- Logo/Title with Home Link -->
			<div class="flex items-center">
				<a href="/" class="text-xl font-semibold text-gray-900 hover:text-blue-600 transition-colors duration-200">
					Chat MAF
				</a>
			</div>

			<!-- Current Route Info -->
			<div class="text-sm text-gray-500">
				{$page.route.id || '/'}
			</div>
		</div>
	</div>
</header>