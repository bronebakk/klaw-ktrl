<script lang="ts">
	import { wizardData, type WizardData } from '$lib/stores/wizard';

	const steps = ['Telegram-bot', 'AI-modell', 'Personlighet', 'Bekreft'];

	// ── State ────────────────────────────────────────────────────────────────
	let currentStep = $state(0);
	let data = $state<WizardData>({
		telegramToken: '',
		aiModel: '',
		apiKey: '',
		personality: '',
		personalityTemplate: ''
	});
	let errors = $state<Record<string, string>>({});

	// Step 0 — Telegram validation
	let telegramValidating = $state(false);
	let telegramValid = $state(false);
	let telegramBotName = $state('');
	let telegramBotUsername = $state('');

	// Step 1 — AI key validation
	let aiKeyValidating = $state(false);
	let aiKeyValid = $state(false);
	let aiKeyModels = $state<string[]>([]);

	// Step 3 — Deploy
	let deployState = $state<'idle' | 'creating' | 'configuring' | 'starting' | 'done' | 'error'>('idle');
	let deployError = $state('');
	let deployedBotUsername = $state('');

	// ── Reference data ────────────────────────────────────────────────────────
	const personalityTemplates = [
		{
			id: 'professional',
			label: 'Profesjonell',
			desc: 'Formell og saklig. Perfekt for jobb.',
			prompt: 'Du er en profesjonell assistent. Vær saklig, presis og hjelpsom.'
		},
		{
			id: 'casual',
			label: 'Uformell',
			desc: 'Avslappet og vennlig. Som en kompis.',
			prompt: 'Du er en avslappet og vennlig assistent. Bruk uformelt språk og vær hyggelig.'
		},
		{
			id: 'creative',
			label: 'Kreativ',
			desc: 'Fantasifull og inspirerende.',
			prompt:
				'Du er en kreativ assistent. Tenk utenfor boksen, vær inspirerende og kom med originale ideer.'
		}
	];

	const aiModels = [
		{
			id: 'claude',
			name: 'Claude',
			provider: 'Anthropic',
			apiProvider: 'anthropic',
			desc: 'Best på lengre samtaler og nyanser'
		},
		{
			id: 'gemini',
			name: 'Gemini',
			provider: 'Google',
			apiProvider: 'google',
			desc: 'Rask og allsidig med bra norsk'
		},
		{
			id: 'gpt',
			name: 'GPT',
			provider: 'OpenAI',
			apiProvider: 'openai',
			desc: 'Pålitelig allrounder'
		}
	];

	// Sync store
	wizardData.subscribe((v) => (data = { ...v }));

	// Reset validation when token changes
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		data.telegramToken;
		telegramValid = false;
		telegramBotName = '';
		telegramBotUsername = '';
	});

	// Reset AI key validation when model or key changes
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		data.aiModel;
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		data.apiKey;
		aiKeyValid = false;
		aiKeyModels = [];
	});

	// ── Validation helpers ────────────────────────────────────────────────────

	async function validateTelegramToken() {
		errors = {};
		if (!data.telegramToken.trim()) {
			errors.telegramToken = 'Bot-token er påkrevd';
			return;
		}
		if (!/^\d+:[A-Za-z0-9_-]{35,}$/.test(data.telegramToken.trim())) {
			errors.telegramToken = 'Ugyldig token-format. Skal se ut som: 123456:ABC-DEF...';
			return;
		}

		telegramValidating = true;
		telegramValid = false;
		try {
			const res = await fetch('/api/validate/telegram-token', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ token: data.telegramToken.trim() })
			});
			const json = await res.json();
			if (res.ok && json.ok) {
				telegramValid = true;
				telegramBotName = json.bot_name;
				telegramBotUsername = json.bot_username;
			} else {
				errors.telegramToken = json.detail ?? 'Ugyldig token';
			}
		} catch {
			errors.telegramToken = 'Klarte ikke å nå Telegram API. Prøv igjen.';
		} finally {
			telegramValidating = false;
		}
	}

	async function validateAIKey() {
		errors = {};
		if (!data.aiModel) {
			errors.aiModel = 'Velg en AI-modell først';
			return;
		}
		if (!data.apiKey.trim()) {
			errors.apiKey = 'API-nøkkel er påkrevd';
			return;
		}

		const modelInfo = aiModels.find((m) => m.id === data.aiModel);
		if (!modelInfo) return;

		aiKeyValidating = true;
		aiKeyValid = false;
		try {
			const res = await fetch('/api/validate/ai-key', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ provider: modelInfo.apiProvider, key: data.apiKey.trim() })
			});
			const json = await res.json();
			if (res.ok && json.ok) {
				aiKeyValid = true;
				aiKeyModels = json.models ?? [];
			} else {
				errors.apiKey = json.detail ?? 'Ugyldig API-nøkkel';
			}
		} catch {
			errors.apiKey = 'Klarte ikke å nå provider API. Prøv igjen.';
		} finally {
			aiKeyValidating = false;
		}
	}

	function validateStep(step: number): boolean {
		errors = {};
		if (step === 0) {
			if (!telegramValid) {
				errors.telegramToken = 'Valider token-et først';
				return false;
			}
		} else if (step === 1) {
			if (!data.aiModel) {
				errors.aiModel = 'Velg en AI-modell';
				return false;
			}
			if (!aiKeyValid) {
				errors.apiKey = 'Valider API-nøkkelen først';
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
	}

	function back() {
		wizardData.set({ ...data });
		if (currentStep > 0) currentStep--;
	}

	function selectTemplate(tmpl: (typeof personalityTemplates)[0]) {
		data.personalityTemplate = tmpl.id;
		data.personality = tmpl.prompt;
	}

	// ── Deploy ────────────────────────────────────────────────────────────────

	async function deploy() {
		deployState = 'creating';
		deployError = '';

		// Build a user_id from the bot username or a timestamp slug
		const userId = telegramBotUsername
			? telegramBotUsername.toLowerCase().replace(/[^a-z0-9_-]/g, '_')
			: `user_${Date.now()}`;

		const modelInfo = aiModels.find((m) => m.id === data.aiModel);

		try {
			// Phase 1 — creating record
			await sleep(600);
			deployState = 'configuring';

			// Phase 2 — call provisioning API
			const res = await fetch('/api/instances', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					user_id: userId,
					telegram_token: data.telegramToken.trim(),
					ai_provider: modelInfo?.apiProvider ?? 'anthropic',
					ai_api_key: data.apiKey.trim(),
					personality: data.personality.trim() || undefined
				})
			});

			const json = await res.json();

			if (!res.ok) {
				throw new Error(json.detail ?? `Server-feil: ${res.status}`);
			}

			deployState = 'starting';
			await sleep(800);

			deployedBotUsername = telegramBotUsername;
			document.cookie = `klaw_user_id=${userId}; path=/; max-age=${60 * 60 * 24 * 365}`;
			deployState = 'done';
		} catch (err: unknown) {
			deployError = err instanceof Error ? err.message : String(err);
			deployState = 'error';
		}
	}

	function sleep(ms: number) {
		return new Promise((r) => setTimeout(r, ms));
	}

	const deploySteps = [
		{ key: 'creating', label: 'Oppretter instans...' },
		{ key: 'configuring', label: 'Konfigurerer OpenClaw...' },
		{ key: 'starting', label: 'Starter bot...' },
		{ key: 'done', label: 'Ferdig!' }
	];

	function deployStepDone(key: string) {
		const order = ['creating', 'configuring', 'starting', 'done'];
		return order.indexOf(deployState) > order.indexOf(key);
	}

	function deployStepActive(key: string) {
		return deployState === key;
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
					<div
						class="w-full h-1 rounded-full {i <= currentStep ? 'bg-accent' : 'bg-border'}"
					></div>
					<span class="text-xs {i <= currentStep ? 'text-accent' : 'text-text-muted'}"
						>{step}</span
					>
				</div>
			{/each}
		</div>

		<!-- ─── Step 0: Telegram ─────────────────────────────────────────────── -->
		{#if currentStep === 0}
			<div>
				<h2 class="text-2xl font-bold mb-2">Lag din Telegram-bot</h2>
				<p class="text-text-muted mb-8">
					Du trenger en Telegram-bot for at assistenten skal kunne motta og sende meldinger.
				</p>

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
					<div class="flex gap-2">
						<input
							type="text"
							bind:value={data.telegramToken}
							placeholder="123456789:ABCdefGHI..."
							class="flex-1 px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted/50 focus:outline-none focus:border-accent font-mono text-sm"
						/>
						<button
							type="button"
							onclick={validateTelegramToken}
							disabled={telegramValidating || !data.telegramToken.trim()}
							class="px-4 py-3 bg-accent hover:bg-accent-hover disabled:opacity-40 text-white font-medium rounded-lg transition-colors text-sm whitespace-nowrap"
						>
							{telegramValidating ? 'Sjekker...' : 'Verifiser'}
						</button>
					</div>
					{#if errors.telegramToken}
						<p class="text-red-400 text-sm mt-2">⚠ {errors.telegramToken}</p>
					{/if}
				</label>

				<!-- Validation result -->
				{#if telegramValid}
					<div
						class="mt-4 p-4 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-3"
					>
						<div
							class="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="white"
								stroke-width="3"
								stroke-linecap="round"
								stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg
							>
						</div>
						<div>
							<div class="font-medium text-green-400">{telegramBotName}</div>
							<div class="text-sm text-text-muted">@{telegramBotUsername}</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- ─── Step 1: AI Model ────────────────────────────────────────────── -->
		{:else if currentStep === 1}
			<div>
				<h2 class="text-2xl font-bold mb-2">Velg AI-modell</h2>
				<p class="text-text-muted mb-8">Hvilken AI skal drive assistenten din? Du kan bytte senere.</p>

				<div class="grid gap-3 mb-8">
					{#each aiModels as model}
						<button
							type="button"
							onclick={() => {
								data.aiModel = model.id as WizardData['aiModel'];
								aiKeyValid = false;
								aiKeyModels = [];
							}}
							class="flex items-center gap-4 p-4 rounded-lg border text-left transition-colors
								{data.aiModel === model.id
								? 'bg-accent/10 border-accent'
								: 'bg-surface border-border hover:border-text-muted/30'}"
						>
							<div
								class="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center text-lg font-bold text-accent"
							>
								{model.name[0]}
							</div>
							<div class="flex-1">
								<div class="font-medium">
									{model.name}
									<span class="text-text-muted text-sm">· {model.provider}</span>
								</div>
								<div class="text-sm text-text-muted">{model.desc}</div>
							</div>
							{#if data.aiModel === model.id}
								<div class="w-5 h-5 rounded-full bg-accent flex items-center justify-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="12"
										height="12"
										viewBox="0 0 24 24"
										fill="none"
										stroke="white"
										stroke-width="3"
										stroke-linecap="round"
										stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg
									>
								</div>
							{/if}
						</button>
					{/each}
				</div>
				{#if errors.aiModel}
					<p class="text-red-400 text-sm mb-4">⚠ {errors.aiModel}</p>
				{/if}

				<label class="block">
					<span class="text-sm font-medium mb-2 block">API-nøkkel</span>
					<div class="flex gap-2">
						<input
							type="password"
							bind:value={data.apiKey}
							placeholder="sk-..."
							class="flex-1 px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted/50 focus:outline-none focus:border-accent font-mono text-sm"
						/>
						<button
							type="button"
							onclick={validateAIKey}
							disabled={aiKeyValidating || !data.apiKey.trim() || !data.aiModel}
							class="px-4 py-3 bg-accent hover:bg-accent-hover disabled:opacity-40 text-white font-medium rounded-lg transition-colors text-sm whitespace-nowrap"
						>
							{aiKeyValidating ? 'Tester...' : 'Test nøkkel'}
						</button>
					</div>
					{#if errors.apiKey}
						<p class="text-red-400 text-sm mt-2">⚠ {errors.apiKey}</p>
					{/if}
					<p class="text-xs text-text-muted mt-2">
						Nøkkelen lagres kryptert og brukes kun for din assistent.
					</p>
				</label>

				<!-- AI key validation result -->
				{#if aiKeyValid}
					<div
						class="mt-4 p-4 rounded-lg bg-green-500/10 border border-green-500/30"
					>
						<div class="flex items-center gap-2 mb-2">
							<div
								class="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="10"
									height="10"
									viewBox="0 0 24 24"
									fill="none"
									stroke="white"
									stroke-width="3"
									stroke-linecap="round"
									stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg
								>
							</div>
							<span class="text-green-400 font-medium text-sm">Nøkkel verifisert</span>
						</div>
						{#if aiKeyModels.length > 0}
							<p class="text-xs text-text-muted">
								Tilgjengelige modeller: {aiKeyModels.slice(0, 3).join(', ')}
							</p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- ─── Step 2: Personality ────────────────────────────────────────── -->
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
								{data.personalityTemplate === tmpl.id
								? 'bg-accent/10 border-accent'
								: 'bg-surface border-border hover:border-text-muted/30'}"
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
						<p class="text-red-400 text-sm mt-2">⚠ {errors.personality}</p>
					{/if}
				</label>
			</div>

			<!-- ─── Step 3: Confirm + Deploy ──────────────────────────────────── -->
		{:else if currentStep === 3}
			<div>
				{#if deployState === 'idle' || deployState === 'error'}
					<h2 class="text-2xl font-bold mb-2">Alt klart!</h2>
					<p class="text-text-muted mb-8">
						Sjekk at alt ser riktig ut før du deployer.
					</p>

					<div class="space-y-4 mb-10">
						<div class="p-4 rounded-lg bg-surface border border-border">
							<div class="text-xs text-text-muted mb-1">Telegram Bot</div>
							<div class="font-medium text-green-400">
								{telegramBotName}
								<span class="text-text-muted font-normal">@{telegramBotUsername}</span>
							</div>
						</div>
						<div class="p-4 rounded-lg bg-surface border border-border">
							<div class="text-xs text-text-muted mb-1">AI-modell</div>
							<div class="font-medium">
								{aiModels.find((m) => m.id === data.aiModel)?.name ?? '—'}
								<span class="text-text-muted"
									>· {aiModels.find((m) => m.id === data.aiModel)?.provider ?? ''}</span
								>
							</div>
						</div>
						<div class="p-4 rounded-lg bg-surface border border-border">
							<div class="text-xs text-text-muted mb-1">Personlighet</div>
							<div class="text-sm text-text-muted">{data.personality}</div>
						</div>
					</div>

					{#if deployState === 'error'}
						<div class="p-4 rounded-lg bg-red-500/10 border border-red-500/30 mb-6">
							<p class="text-red-400 text-sm font-medium">Deployment feilet</p>
							<p class="text-red-300 text-sm mt-1">{deployError}</p>
						</div>
					{/if}

					<button
						type="button"
						onclick={deploy}
						class="w-full py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors"
					>
						{deployState === 'error' ? '↻ Prøv igjen' : '🚀 Deploy assistenten'}
					</button>

				{:else if deployState === 'done'}
					<!-- Success state -->
					<div class="text-center py-8">
						<div
							class="w-20 h-20 rounded-full bg-green-500/20 border-2 border-green-500 flex items-center justify-center mx-auto mb-6"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="36"
								height="36"
								viewBox="0 0 24 24"
								fill="none"
								stroke="#22c55e"
								stroke-width="2.5"
								stroke-linecap="round"
								stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg
							>
						</div>
						<h2 class="text-2xl font-bold mb-2">Boten din er live! 🎉</h2>
						<p class="text-text-muted mb-8">Din OpenClaw-assistent kjører nå på Telegram.</p>

						<a
							href="https://t.me/{deployedBotUsername}"
							target="_blank"
							rel="noopener noreferrer"
							class="inline-block px-8 py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors mb-4"
						>
							Åpne @{deployedBotUsername} i Telegram →
						</a>

						<div class="mt-8">
							<a href="/dashboard" class="text-sm text-text-muted hover:text-text transition-colors">
								Gå til dashboard →
							</a>
						</div>
					</div>

				{:else}
					<!-- Progress state -->
					<div class="py-8">
						<h2 class="text-2xl font-bold mb-2">Deployer...</h2>
						<p class="text-text-muted mb-10">Setter opp din personlige assistent.</p>

						<div class="space-y-4">
							{#each deploySteps as step}
								{@const done = deployStepDone(step.key)}
								{@const active = deployStepActive(step.key)}
								<div class="flex items-center gap-4">
									<div
										class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors
											{done
											? 'bg-green-500'
											: active
												? 'bg-accent animate-pulse'
												: 'bg-border'}"
									>
										{#if done}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												width="14"
												height="14"
												viewBox="0 0 24 24"
												fill="none"
												stroke="white"
												stroke-width="3"
												stroke-linecap="round"
												stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg
											>
										{:else if active}
											<div class="w-3 h-3 rounded-full bg-white/80"></div>
										{/if}
									</div>
									<span
										class="text-sm {done
											? 'text-green-400'
											: active
												? 'text-text font-medium'
												: 'text-text-muted'}">{step.label}</span
									>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Navigation -->
		{#if currentStep < 3}
			<div class="flex items-center justify-between mt-12 pt-6 border-t border-border">
				{#if currentStep > 0}
					<button
						type="button"
						onclick={back}
						class="px-6 py-2.5 text-sm text-text-muted hover:text-text transition-colors"
					>
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
		{:else if deployState === 'idle' || deployState === 'error'}
			<div class="mt-6">
				<button
					type="button"
					onclick={back}
					class="text-sm text-text-muted hover:text-text transition-colors"
				>
					← Tilbake
				</button>
			</div>
		{/if}
	</main>
</div>
