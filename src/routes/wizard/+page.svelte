<script lang="ts">
	import { wizardData, wizardStep, type WizardData } from '$lib/stores/wizard';

	const steps = ['Telegram-bot', 'AI-modell', 'Personlighet', 'Bekreft'];

	let currentStep = $state(0);
	let data = $state<WizardData>({
		telegramToken: '',
		aiModel: '',
		apiKey: '',
		personality: '',
		personalityTemplate: ''
	});
	let errors = $state<Record<string, string>>({});
	let deploying = $state(false);

	// Sync with store
	wizardData.subscribe((v) => (data = { ...v }));

	const personalityTemplates = [
		{ id: 'professional', label: 'Profesjonell', desc: 'Formell og saklig. Perfekt for jobb.', prompt: 'Du er en profesjonell assistent. Vær saklig, presis og hjelpsom.' },
		{ id: 'casual', label: 'Uformell', desc: 'Avslappet og vennlig. Som en kompis.', prompt: 'Du er en avslappet og vennlig assistent. Bruk uformelt språk og vær hyggelig.' },
		{ id: 'creative', label: 'Kreativ', desc: 'Fantasifull og inspirerende.', prompt: 'Du er en kreativ assistent. Tenk utenfor boksen, vær inspirerende og kom med originale ideer.' }
	];

	const aiModels = [
		{ id: 'claude', name: 'Claude', provider: 'Anthropic', desc: 'Best på lengre samtaler og nyanser' },
		{ id: 'gemini', name: 'Gemini', provider: 'Google', desc: 'Rask og allsidig med bra norsk' },
		{ id: 'gpt', name: 'GPT', provider: 'OpenAI', desc: 'Pålitelig allrounder' }
	];

	function validateStep(step: number): boolean {
		errors = {};
		if (step === 0) {
			if (!data.telegramToken.trim()) {
				errors.telegramToken = 'Bot-token er påkrevd';
				return false;
			}
			if (!/^\d+:[A-Za-z0-9_-]{35,}$/.test(data.telegramToken.trim())) {
				errors.telegramToken = 'Ugyldig token-format. Skal se ut som: 123456:ABC-DEF...';
				return false;
			}
		} else if (step === 1) {
			if (!data.aiModel) {
				errors.aiModel = 'Velg en AI-modell';
				return false;
			}
			if (!data.apiKey.trim()) {
				errors.apiKey = 'API-nøkkel er påkrevd';
				return false;
			}
		} else if (step === 2) {
			if (!data.personality.trim()) {
				errors.personality = 'Beskriv personligheten til assistenten din';
				return false;
			}
		}
		return true;
	}

	function next() {
		if (!validateStep(currentStep)) return;
		wizardData.set({ ...data });
		if (currentStep < steps.length - 1) currentStep++;
		wizardStep.set(currentStep);
	}

	function back() {
		wizardData.set({ ...data });
		if (currentStep > 0) currentStep--;
		wizardStep.set(currentStep);
	}

	function selectTemplate(tmpl: typeof personalityTemplates[0]) {
		data.personalityTemplate = tmpl.id;
		data.personality = tmpl.prompt;
	}

	async function deploy() {
		deploying = true;
		// TODO: API call
		await new Promise((r) => setTimeout(r, 2000));
		deploying = false;
		alert('Deploy kommer snart! Backend er ikke klar ennå.');
	}
</script>

<div class="min-h-screen flex flex-col">
	<!-- Header -->
	<nav class="flex items-center justify-between px-6 py-4 max-w-4xl mx-auto w-full">
		<a href="/" class="text-xl font-bold tracking-tight text-text">klaw</a>
		<span class="text-sm text-text-muted">Steg {currentStep + 1} av {steps.length}</span>
	</nav>

	<main class="flex-1 flex flex-col px-6 max-w-2xl mx-auto w-full py-8">
		<!-- Progress -->
		<div class="flex items-center gap-1 mb-12">
			{#each steps as step, i}
				<div class="flex-1 flex flex-col items-center gap-2">
					<div class="w-full h-1 rounded-full {i <= currentStep ? 'bg-accent' : 'bg-border'}"></div>
					<span class="text-xs {i <= currentStep ? 'text-accent' : 'text-text-muted'}">{step}</span>
				</div>
			{/each}
		</div>

		<!-- Step 0: Telegram -->
		{#if currentStep === 0}
			<div>
				<h2 class="text-2xl font-bold mb-2">Lag din Telegram-bot</h2>
				<p class="text-text-muted mb-8">Du trenger en Telegram-bot for at assistenten skal kunne motta og sende meldinger.</p>

				<div class="p-4 rounded-lg bg-surface border border-border mb-6">
					<h3 class="font-medium mb-3 text-sm">Slik gjør du:</h3>
					<ol class="text-sm text-text-muted space-y-2 list-decimal list-inside">
						<li>Åpne Telegram og søk etter <strong class="text-text">@BotFather</strong></li>
						<li>Send <code class="px-1.5 py-0.5 bg-border rounded text-text">/newbot</code></li>
						<li>Velg et navn og brukernavn for boten</li>
						<li>Kopier tokenet du får tilbake</li>
					</ol>
				</div>

				<label class="block">
					<span class="text-sm font-medium mb-2 block">Bot Token</span>
					<input
						type="text"
						bind:value={data.telegramToken}
						placeholder="123456789:ABCdefGHI..."
						class="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted/50 focus:outline-none focus:border-accent font-mono text-sm"
					/>
					{#if errors.telegramToken}
						<p class="text-red-400 text-sm mt-2">{errors.telegramToken}</p>
					{/if}
				</label>
			</div>

		<!-- Step 1: AI Model -->
		{:else if currentStep === 1}
			<div>
				<h2 class="text-2xl font-bold mb-2">Velg AI-modell</h2>
				<p class="text-text-muted mb-8">Hvilken AI skal drive assistenten din? Du kan bytte senere.</p>

				<div class="grid gap-3 mb-8">
					{#each aiModels as model}
						<button
							type="button"
							onclick={() => (data.aiModel = model.id as WizardData['aiModel'])}
							class="flex items-center gap-4 p-4 rounded-lg border text-left transition-colors
								{data.aiModel === model.id ? 'bg-accent/10 border-accent' : 'bg-surface border-border hover:border-text-muted/30'}"
						>
							<div class="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center text-lg font-bold text-accent">
								{model.name[0]}
							</div>
							<div class="flex-1">
								<div class="font-medium">{model.name} <span class="text-text-muted text-sm">· {model.provider}</span></div>
								<div class="text-sm text-text-muted">{model.desc}</div>
							</div>
							{#if data.aiModel === model.id}
								<div class="w-5 h-5 rounded-full bg-accent flex items-center justify-center">
									<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
								</div>
							{/if}
						</button>
					{/each}
				</div>
				{#if errors.aiModel}
					<p class="text-red-400 text-sm mb-4">{errors.aiModel}</p>
				{/if}

				<label class="block">
					<span class="text-sm font-medium mb-2 block">API-nøkkel</span>
					<input
						type="password"
						bind:value={data.apiKey}
						placeholder="sk-..."
						class="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted/50 focus:outline-none focus:border-accent font-mono text-sm"
					/>
					{#if errors.apiKey}
						<p class="text-red-400 text-sm mt-2">{errors.apiKey}</p>
					{/if}
					<p class="text-xs text-text-muted mt-2">Nøkkelen lagres kryptert og brukes kun for din assistent.</p>
				</label>
			</div>

		<!-- Step 2: Personality -->
		{:else if currentStep === 2}
			<div>
				<h2 class="text-2xl font-bold mb-2">Gi assistenten personlighet</h2>
				<p class="text-text-muted mb-8">Velg en mal eller skriv din egen beskrivelse.</p>

				<div class="grid gap-3 mb-6">
					{#each personalityTemplates as tmpl}
						<button
							type="button"
							onclick={() => selectTemplate(tmpl)}
							class="flex items-start gap-3 p-4 rounded-lg border text-left transition-colors
								{data.personalityTemplate === tmpl.id ? 'bg-accent/10 border-accent' : 'bg-surface border-border hover:border-text-muted/30'}"
						>
							<div class="flex-1">
								<div class="font-medium">{tmpl.label}</div>
								<div class="text-sm text-text-muted">{tmpl.desc}</div>
							</div>
						</button>
					{/each}
				</div>

				<label class="block">
					<span class="text-sm font-medium mb-2 block">Instruksjoner til assistenten</span>
					<textarea
						bind:value={data.personality}
						rows="4"
						placeholder="Beskriv hvordan assistenten din skal oppføre seg..."
						class="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted/50 focus:outline-none focus:border-accent text-sm resize-none"
					></textarea>
					{#if errors.personality}
						<p class="text-red-400 text-sm mt-2">{errors.personality}</p>
					{/if}
				</label>
			</div>

		<!-- Step 3: Confirm -->
		{:else if currentStep === 3}
			<div>
				<h2 class="text-2xl font-bold mb-2">Alt klart!</h2>
				<p class="text-text-muted mb-8">Sjekk at alt ser riktig ut før du deployer.</p>

				<div class="space-y-4 mb-10">
					<div class="p-4 rounded-lg bg-surface border border-border">
						<div class="text-xs text-text-muted mb-1">Telegram Bot</div>
						<div class="font-mono text-sm">{data.telegramToken.slice(0, 10)}...{data.telegramToken.slice(-6)}</div>
					</div>
					<div class="p-4 rounded-lg bg-surface border border-border">
						<div class="text-xs text-text-muted mb-1">AI-modell</div>
						<div class="font-medium">{aiModels.find((m) => m.id === data.aiModel)?.name ?? '—'} <span class="text-text-muted">· {aiModels.find((m) => m.id === data.aiModel)?.provider ?? ''}</span></div>
					</div>
					<div class="p-4 rounded-lg bg-surface border border-border">
						<div class="text-xs text-text-muted mb-1">Personlighet</div>
						<div class="text-sm text-text-muted">{data.personality}</div>
					</div>
				</div>

				<button
					type="button"
					onclick={deploy}
					disabled={deploying}
					class="w-full py-3 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white font-semibold rounded-lg transition-colors"
				>
					{deploying ? 'Deployer...' : '🚀 Deploy assistenten'}
				</button>
			</div>
		{/if}

		<!-- Navigation -->
		{#if currentStep < 3}
			<div class="flex items-center justify-between mt-12 pt-6 border-t border-border">
				{#if currentStep > 0}
					<button type="button" onclick={back} class="px-6 py-2.5 text-sm text-text-muted hover:text-text transition-colors">
						← Tilbake
					</button>
				{:else}
					<div></div>
				{/if}
				<button
					type="button"
					onclick={next}
					class="px-8 py-2.5 bg-accent hover:bg-accent-hover text-white font-medium rounded-lg transition-colors text-sm"
				>
					Neste →
				</button>
			</div>
		{:else}
			<div class="mt-6">
				<button type="button" onclick={back} class="text-sm text-text-muted hover:text-text transition-colors">
					← Tilbake
				</button>
			</div>
		{/if}
	</main>
</div>
