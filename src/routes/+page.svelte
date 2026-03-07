<script lang="ts">
	import { onMount } from 'svelte';

	let hasInstance = $state(false);

	onMount(() => {
		hasInstance = document.cookie.split(';').some((c) => c.trim().startsWith('klaw_user_id='));
	});
</script>

<div class="flex flex-col min-h-screen">
	<!-- Nav -->
	<nav class="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto w-full">
		<a href="/" class="text-xl font-bold tracking-tight text-text">klaw</a>
		<a href="/wizard" class="text-sm text-text-muted hover:text-text transition-colors">Logg inn</a>
	</nav>

	<!-- Hero -->
	<main class="flex-1 flex flex-col items-center justify-center px-6 text-center">
		<div class="max-w-2xl mx-auto">
			<div class="inline-flex items-center gap-2 px-3 py-1 mb-8 text-xs font-medium text-accent bg-accent/10 rounded-full border border-accent/20">
				<span class="w-1.5 h-1.5 bg-accent rounded-full"></span>
				Nå i beta
			</div>

			<h1 class="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-tight mb-6">
				Din egen AI-assistent.<br />
				<span class="text-text-muted">Satt opp på 5 minutter.</span>
			</h1>

			<p class="text-lg text-text-muted max-w-lg mx-auto mb-10 leading-relaxed">
				Koble til Telegram, velg din foretrukne AI-modell, gi den en personlighet — og du har en assistent som er tilgjengelig 24/7.
			</p>

			<div class="flex flex-col sm:flex-row items-center justify-center gap-4">
				{#if hasInstance}
					<a
						href="/dashboard"
						class="inline-flex items-center gap-2 px-8 py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors text-base"
					>
						Gå til Dashboard
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
					</a>
				{:else}
					<a
						href="/wizard"
						class="inline-flex items-center gap-2 px-8 py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors text-base"
					>
						Kom i gang
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
					</a>
				{/if}
				<a href="#features" class="text-sm text-text-muted hover:text-text transition-colors">
					Les mer ↓
				</a>
			</div>
		</div>
	</main>

	<!-- Features -->
	<section id="features" class="px-6 py-24 max-w-5xl mx-auto w-full">
		<div class="grid md:grid-cols-3 gap-8">
			<div class="p-6 rounded-xl bg-surface border border-border">
				<div class="w-10 h-10 flex items-center justify-center rounded-lg bg-accent/10 text-accent mb-4 text-xl">💬</div>
				<h3 class="font-semibold mb-2">Telegram-integrasjon</h3>
				<p class="text-sm text-text-muted leading-relaxed">Snakk med assistenten din direkte i Telegram. Ingen app å installere — bruk det du allerede har.</p>
			</div>
			<div class="p-6 rounded-xl bg-surface border border-border">
				<div class="w-10 h-10 flex items-center justify-center rounded-lg bg-accent/10 text-accent mb-4 text-xl">🧠</div>
				<h3 class="font-semibold mb-2">Velg AI-modell</h3>
				<p class="text-sm text-text-muted leading-relaxed">Claude, Gemini eller GPT — du velger hvilken hjerne assistenten din skal bruke.</p>
			</div>
			<div class="p-6 rounded-xl bg-surface border border-border">
				<div class="w-10 h-10 flex items-center justify-center rounded-lg bg-accent/10 text-accent mb-4 text-xl">✨</div>
				<h3 class="font-semibold mb-2">Din personlighet</h3>
				<p class="text-sm text-text-muted leading-relaxed">Gi assistenten en unik personlighet. Profesjonell, uformell, eller noe helt eget.</p>
			</div>
		</div>
	</section>

	<!-- Footer -->
	<footer class="px-6 py-8 text-center text-xs text-text-muted border-t border-border">
		<p>© 2026 Klaw · Drevet av <a href="https://openclaw.com" class="text-accent hover:text-accent-hover transition-colors">OpenClaw</a></p>
	</footer>
</div>
