/**
 * Workflow step configuration
 * Maps executor IDs to user-friendly step names and descriptions
 */

export interface StepInfo {
	emoji: string;
	name: string;
	description: string;
}

export const WORKFLOW_STEPS: Record<string, StepInfo> = {
	initialize_context: {
		emoji: '🔄',
		name: 'Initializing',
		description: 'Setting up workflow context'
	},
	schema_understanding_agent: {
		emoji: '🗄️',
		name: 'Analyzing Schema',
		description: 'Understanding database structure'
	},
	parse_schema_selection: {
		emoji: '📋',
		name: 'Loading Schema',
		description: 'Loading detailed schema information'
	},
	sql_generation_agent: {
		emoji: '⚡',
		name: 'Generating SQL',
		description: 'Creating SQL query'
	},
	parse_sql_generation: {
		emoji: '▶️',
		name: 'Executing Query',
		description: 'Running SQL against database'
	},
	handle_success: {
		emoji: '✅',
		name: 'Success',
		description: 'Formatting response'
	},
	handle_syntax_error: {
		emoji: '🔧',
		name: 'Fixing Syntax',
		description: 'Correcting SQL syntax error'
	},
	handle_semantic_error: {
		emoji: '🔍',
		name: 'Re-analyzing',
		description: 'Re-evaluating schema selection'
	},
	handle_execution_issue: {
		emoji: '⚠️',
		name: 'Handling Issue',
		description: 'Addressing execution problem'
	}
};

export function getStepDisplay(executorId: string, summary?: string): string {
	const step = WORKFLOW_STEPS[executorId];
	
	if (!step) {
		return executorId;
	}

	const baseDisplay = `${step.emoji} ${step.name}`;
	
	if (summary) {
		return `${baseDisplay} ${summary}`;
	}
	
	return baseDisplay;
}

export function getStepDescription(executorId: string): string {
	const step = WORKFLOW_STEPS[executorId];
	return step?.description || 'Processing...';
}
