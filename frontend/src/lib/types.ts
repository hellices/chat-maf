export interface Message {
	role: 'user' | 'assistant';
	content: string;
}

export interface ChatRequest {
	message: string;
	instruction: string;
}

// Database Schema Types
export interface Column {
	name: string;
	type: string;
	primary_key: boolean;
	foreign_key?: {
		table: string;
		column: string;
	} | null;
}

export interface Table {
	name: string;
	columns: Column[];
}

export interface DatabaseSchema {
	database: string;
	tables: Table[];
}

export interface Relationship {
	from: { table: string; column: string };
	to: { table: string; column: string };
}