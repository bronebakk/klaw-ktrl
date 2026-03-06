import { writable } from 'svelte/store';

export interface WizardData {
	telegramToken: string;
	aiModel: 'claude' | 'gemini' | 'gpt' | '';
	apiKey: string;
	personality: string;
	personalityTemplate: string;
}

export const wizardData = writable<WizardData>({
	telegramToken: '',
	aiModel: '',
	apiKey: '',
	personality: '',
	personalityTemplate: ''
});

export const wizardStep = writable(0);
