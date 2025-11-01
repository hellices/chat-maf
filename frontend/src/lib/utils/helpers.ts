/**
 * Utility functions for NL2SQL features
 */

/**
 * Debounce function to limit how often a function can be called
 */
export function debounce<T extends (...args: any[]) => any>(
	func: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout> | null = null;

	return function executedFunction(...args: Parameters<T>) {
		const later = () => {
			timeout = null;
			func(...args);
		};

		if (timeout) {
			clearTimeout(timeout);
		}
		timeout = setTimeout(later, wait);
	};
}

/**
 * Scroll to bottom of element with smooth animation
 */
export async function scrollToBottom(element: HTMLElement | null, behavior: ScrollBehavior = 'smooth'): Promise<void> {
	if (!element) return;
	
	// Small delay to ensure DOM is updated
	await new Promise(resolve => setTimeout(resolve, 10));
	
	element.scrollTo({
		top: element.scrollHeight,
		behavior
	});
}

/**
 * Format large numbers with thousand separators
 */
export function formatNumber(num: number): string {
	return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Format execution time in milliseconds
 */
export function formatExecutionTime(ms: number): string {
	if (ms < 1000) {
		return `${Math.round(ms)}ms`;
	}
	return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Truncate string to max length with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
	if (str.length <= maxLength) return str;
	return str.substring(0, maxLength - 3) + '...';
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch (err) {
		console.error('Failed to copy:', err);
		return false;
	}
}

/**
 * Download text as file
 */
export function downloadAsFile(content: string, filename: string, mimeType: string = 'text/plain'): void {
	const blob = new Blob([content], { type: mimeType });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	URL.revokeObjectURL(url);
}
