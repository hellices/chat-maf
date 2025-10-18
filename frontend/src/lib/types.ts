export interface Message {
	role: 'user' | 'assistant';
	content: string;
}

export interface ChatRequest {
	message: string;
	instruction: string;
}