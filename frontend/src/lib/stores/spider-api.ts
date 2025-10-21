import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { DatabaseSchema } from '$lib/types';

export interface SpiderTableSample {
	columns: string[];
	rows: any[];
}

export interface SpiderDatabase {
	name: string;
	description?: string;
}

/**
 * Fetch sample data from a specific table in the Spider database
 */
export async function fetchTableSample(
	database: string,
	tableName: string,
	limit: number = 5
): Promise<SpiderTableSample> {
	const response = await fetch(
		`${PUBLIC_API_BASE_URL}/spider/databases/${database}/tables/${tableName}/sample?limit=${limit}`
	);
	
	if (!response.ok) {
		throw new Error(`Failed to fetch sample data for ${tableName}: ${response.statusText}`);
	}
	
	return await response.json();
}

/**
 * Fetch the schema for a specific database
 */
export async function fetchDatabaseSchema(database: string): Promise<DatabaseSchema> {
	const response = await fetch(
		`${PUBLIC_API_BASE_URL}/spider/databases/${database}/schema`
	);
	
	if (!response.ok) {
		throw new Error(`Failed to fetch schema for ${database}: ${response.statusText}`);
	}
	
	return await response.json();
}

/**
 * Fetch list of available databases
 */
export async function fetchDatabases(): Promise<SpiderDatabase[]> {
	const response = await fetch(`${PUBLIC_API_BASE_URL}/spider/databases`);
	
	if (!response.ok) {
		throw new Error(`Failed to fetch databases: ${response.statusText}`);
	}
	
	return await response.json();
}
