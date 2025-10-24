/**
 * NL2SQL Store - Centralized state management
 */

import { writable, derived } from 'svelte/store';

export interface Message {
	id?: string; // Optional unique identifier for keyed each
	role: 'user' | 'assistant';
	content: string;
	sql?: string;
	result?: any;
	database?: string;
	reasoning_evaluation?: {
		is_correct: boolean | null;
		confidence: number;
		explanation: string;
		suggestions: string;
	};
}

export interface StreamingLog {
	id: string; // Unique identifier
	stepName: string;
	stepLabel: string;
	stepCategory?: string; // Category from backend: 'initialization', 'schema', 'sql', 'result', 'error'
	content: string;
	timestamp: number;
	isExpanded: boolean;
}

export interface NL2SQLState {
	// Messages
	messages: Message[];
	currentMessage: string;

	// Loading state
	isLoading: boolean;
	currentStep: string;
	streamingLogs: StreamingLog[];

	// Database state
	databases: string[];
	selectedDatabase: string | null;
	selectedTables: string[];
	databaseSchema: any | null;

	// UI state
	showSidebar: boolean;
	showInfoModal: boolean;
	loadingDatabases: boolean;
	loadingSchema: boolean;
}

const initialState: NL2SQLState = {
	messages: [],
	currentMessage: '',
	isLoading: false,
	currentStep: '',
	streamingLogs: [],
	databases: [],
	selectedDatabase: null,
	selectedTables: [],
	databaseSchema: null,
	showSidebar: true,
	showInfoModal: false,
	loadingDatabases: false,
	loadingSchema: false
};

function createNL2SQLStore() {
	const { subscribe, set, update } = writable<NL2SQLState>(initialState);

	return {
		subscribe,
		set,
		update,

		// Message actions
		addMessage: (message: Message) =>
			update((state) => {
				// Ensure message has an id
				const messageWithId = {
					...message,
					id: message.id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
				};
				return {
					...state,
					messages: [...state.messages, messageWithId]
				};
			}),

		setCurrentMessage: (message: string) =>
			update((state) => ({
				...state,
				currentMessage: message
			})),

		clearMessages: () =>
			update((state) => ({
				...state,
				messages: [],
				streamingLogs: [],
				currentStep: '',
				isLoading: false
			})),

		// Loading actions
		setLoading: (isLoading: boolean, currentStep: string = '') =>
			update((state) => ({
				...state,
				isLoading,
				currentStep
			})),

		setCurrentStep: (currentStep: string) =>
			update((state) => ({
				...state,
				currentStep
			})),

		// Streaming log actions
		addStreamingLog: (
			stepName: string,
			stepLabel: string,
			content: string,
			stepCategory?: string
		) =>
			update((state) => {
				// Find the most recent log with the same stepName (search from end)
				let lastMatchingIndex = -1;
				for (let i = state.streamingLogs.length - 1; i >= 0; i--) {
					if (state.streamingLogs[i].stepName === stepName) {
						lastMatchingIndex = i;
						break;
					}
				}

				if (lastMatchingIndex >= 0) {
					// Append to the most recent log with same stepName
					const updatedLogs = [...state.streamingLogs];
					updatedLogs[lastMatchingIndex] = {
						...updatedLogs[lastMatchingIndex],
						content: updatedLogs[lastMatchingIndex].content + content,
						timestamp: Date.now()
					};
					return { ...state, streamingLogs: updatedLogs };
				} else {
					// Create new log entry with unique ID
					const id = `${stepName}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
					return {
						...state,
						streamingLogs: [
							...state.streamingLogs,
							{
								id,
								stepName,
								stepLabel,
								stepCategory,
								content,
								timestamp: Date.now(),
								isExpanded: true // Start expanded
							}
						]
					};
				}
			}),

		toggleStreamingLog: (id: string) =>
			update((state) => ({
				...state,
				streamingLogs: state.streamingLogs.map((log) =>
					log.id === id ? { ...log, isExpanded: !log.isExpanded } : log
				)
			})),

		clearStreamingLogs: () =>
			update((state) => ({
				...state,
				streamingLogs: []
			})),

		// Database actions
		setDatabases: (databases: string[]) =>
			update((state) => ({
				...state,
				databases,
				loadingDatabases: false
			})),

		setSelectedDatabase: (database: string | null) =>
			update((state) => ({
				...state,
				selectedDatabase: database,
				selectedTables: database === state.selectedDatabase ? state.selectedTables : []
			})),

		setDatabaseSchema: (schema: any) =>
			update((state) => ({
				...state,
				databaseSchema: schema,
				loadingSchema: false
			})),

		toggleTableSelection: (tableName: string) =>
			update((state) => {
				const index = state.selectedTables.indexOf(tableName);
				const selectedTables =
					index > -1
						? state.selectedTables.filter((t) => t !== tableName)
						: [...state.selectedTables, tableName];

				return {
					...state,
					selectedTables
				};
			}),

		// UI actions
		toggleSidebar: () =>
			update((state) => ({
				...state,
				showSidebar: !state.showSidebar
			})),

		setSidebarVisible: (visible: boolean) =>
			update((state) => ({
				...state,
				showSidebar: visible
			})),

		toggleInfoModal: () =>
			update((state) => ({
				...state,
				showInfoModal: !state.showInfoModal
			})),

		setInfoModalVisible: (visible: boolean) =>
			update((state) => ({
				...state,
				showInfoModal: visible
			})),

		setLoadingDatabases: (loading: boolean) =>
			update((state) => ({
				...state,
				loadingDatabases: loading
			})),

		setLoadingSchema: (loading: boolean) =>
			update((state) => ({
				...state,
				loadingSchema: loading
			})),

		// Reset
		reset: () => set(initialState)
	};
}

export const nl2sqlStore = createNL2SQLStore();

// Derived stores
export const hasActiveQuery = derived(nl2sqlStore, ($store) => $store.isLoading);

export const hasMessages = derived(nl2sqlStore, ($store) => $store.messages.length > 0);

export const canSubmit = derived(
	nl2sqlStore,
	($store) => !$store.isLoading && $store.currentMessage.trim().length > 0
);
