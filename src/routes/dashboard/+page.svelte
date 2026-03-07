<script lang="ts">
	import { onMount } from 'svelte';

	// ── Types ──────────────────────────────────────────────────────────────
	interface InstanceData {
		user_id: string;
		status: 'pending' | 'running' | 'stopped' | 'error' | 'archived';
		container_name: string;
		created_at: string;
		started_at: string;
		uptime_seconds: number;
		health: string;
	}

	// ── State ──────────────────────────────────────────────────────────────
	let userId = $state('');
	let instance = $state<InstanceData | null>(null);
	let loading = $state(true);
	let error = $state('');
	let restarting = $state(false);
	let deleting = $state(false);
	let showDeleteModal = $state(false);
	let refreshInterval = $state<ReturnType<typeof setInterval> | null>(null);

	// ── Cookie helpers ─────────────────────────────────────────────────────
	function getCookie(name: string): string {
		const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
		return match ? decodeURIComponent(match[2]) : '';
	}

	function clearCookie(name: string) {
		document.cookie = `${name}=; path=/; max-age=0`;
	}

	// ── Data fetching ──────────────────────────────────────────────────────
	async function fetchInstance() {
		if (!userId) return;
		try {
			const res = await fetch(`/api/instances/${encodeURIComponent(userId)}`);
			if (!res.ok) {
				if (res.status === 404) {
					error = 'Instansen ble ikke funnet. Den kan ha blitt slettet.';
					instance = null;
				} else {
					throw new Error(`API-feil: ${res.status}`);
				}
				return;
			}
			instance = await res.json();
			error = '';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Kunne ikke hente instans-data';
		} finally {
			loading = false;
		}
	}

	// ── Actions ────────────────────────────────────────────────────────────
	async function restart() {
		if (restarting || !userId) return;
		restarting = true;
		try {
			const res = await fetch(`/api/instances/${encodeURIComponent(userId)}/restart`, {
				method: 'POST'
			});
			if (!res.ok) throw new Error(`Restart feilet: ${res.status}`);
			// Refresh after a short delay to let the container start
			setTimeout(fetchInstance, 2000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Restart feilet';
		} finally {
			restarting = false;
		}
	}

	async function deleteInstance() {
		if (deleting || !userId) return;
		deleting = true;
		try {
			const res = await fetch(`/api/instances/${encodeURIComponent(userId)}`, {
				method: 'DELETE'
			});
			if (!res.ok) throw new Error(`Sletting feilet: ${res.status}`);
			clearCookie('klaw_user_id');
			window.location.href = '/';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Sletting feilet';
			deleting = false;
			showDeleteModal = false;
		}
	}

	function logout() {
		clearCookie('klaw_user_id');
		window.location.href = '/';
	}

	// ── Formatting ─────────────────────────────────────────────────────────
	function formatUptime(seconds: number | undefined | null): string {
		if (!seconds || seconds <= 0) return '';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}t ${m}m`;
		return `${m}m`;
	}

	function statusConfig(status: string) {
		switch (status) {
			case 'running':
				return { label: 'Online', color: 'bg-green-500', textColor: 'text-green-400' };
			case 'pending':
				return { label: 'Starter...', color: 'bg-yellow-500', textColor: 'text-yellow-400' };
			case 'stopped':
			case 'error':
				return { label: 'Offline', color: 'bg-red-500', textColor: 'text-red-400' };
			case 'archived':
				return { label: 'Arkivert', color: 'bg-gray-500', textColor: 'text-gray-400' };
			default:
				return { label: status, color: 'bg-gray-500', textColor: 'text-gray-400' };
		}
	}

	// ── Lifecycle ──────────────────────────────────────────────────────────
	onMount(() => {
		userId = getCookie('klaw_user_id');
		if (!userId) {
			loading = false;
			return;
		}
		fetchInstance();
		refreshInterval = setInterval(fetchInstance, 30000);
		return () => {
			if (refreshInterval) clearInterval(refreshInterval);
		};
	});
</script>

{#if !userId && !loading}
	<!-- No user — login prompt -->
	<div class="min-h-screen flex items-center justify-center px-6">
		<div class="max-w-md w-full text-center">
			<div class="text-5xl mb-6">🔒</div>
			<h1 class="text-2xl font-bold mb-3">Logg inn</h1>
			<p class="text-text-muted mb-8">Du må sette opp en bot før du kan bruke dashboardet.</p>
			<a
				href="/wizard"
				class="inline-flex items-center gap-2 px-8 py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors"
			>
				Sett opp din bot →
			</a>
		</div>
	</div>
{:else}
	<div class="min-h-screen flex flex-col">
		<!-- Navbar -->
		<nav class="border-b border-border">
			<div class="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto w-full">
				<div class="flex items-center gap-8">
					<a href="/" class="text-xl font-bold tracking-tight text-text">klaw</a>
					<div class="flex items-center gap-1">
						<a
							href="/dashboard"
							class="px-3 py-1.5 text-sm font-medium text-accent bg-accent/10 rounded-lg"
						>
							Dashboard
						</a>
						<span
							class="px-3 py-1.5 text-sm text-text-muted cursor-default"
							title="Kommer snart"
						>
							Innstillinger
						</span>
					</div>
				</div>
				<button
					onclick={logout}
					class="px-4 py-1.5 text-sm text-text-muted hover:text-text border border-border hover:border-text-muted/30 rounded-lg transition-colors"
				>
					Logg ut
				</button>
			</div>
		</nav>

		<!-- Main content -->
		<main class="flex-1 px-6 py-8 max-w-6xl mx-auto w-full">
			{#if loading}
				<!-- Loading skeleton -->
				<div class="space-y-6">
					<div class="h-32 bg-surface border border-border rounded-xl animate-pulse"></div>
					<div class="grid md:grid-cols-2 gap-6">
						<div class="h-48 bg-surface border border-border rounded-xl animate-pulse"></div>
						<div class="h-48 bg-surface border border-border rounded-xl animate-pulse"></div>
					</div>
					<div class="h-32 bg-surface border border-border rounded-xl animate-pulse"></div>
				</div>
			{:else if error && !instance}
				<!-- Error state -->
				<div class="p-6 rounded-xl bg-red-500/10 border border-red-500/30 text-center">
					<div class="text-3xl mb-4">⚠️</div>
					<h2 class="text-lg font-semibold text-red-400 mb-2">Noe gikk galt</h2>
					<p class="text-text-muted text-sm mb-6">{error}</p>
					<button
						onclick={fetchInstance}
						class="px-6 py-2.5 bg-accent hover:bg-accent-hover text-white font-medium rounded-lg transition-colors text-sm"
					>
						Prøv igjen
					</button>
				</div>
			{:else if instance}
				{@const status = statusConfig(instance.status)}
				<div class="space-y-6">
					<!-- Card 1: Bot Status -->
					<div class="p-6 rounded-xl bg-surface border border-border">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-4">
								<div
									class="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center text-2xl"
								>
									🤖
								</div>
								<div>
									<div class="flex items-center gap-3">
										<h2 class="text-lg font-semibold">{instance.container_name || instance.user_id}</h2>
										<span
											class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium {status.textColor} bg-current/10"
										>
											<span class="w-1.5 h-1.5 rounded-full {status.color}"></span>
											{status.label}
										</span>
									</div>
									<p class="text-sm text-text-muted mt-0.5">
										ID: {instance.user_id}
										{#if instance.uptime_seconds && instance.status === 'running'}
											<span class="ml-3">·</span>
											<span class="ml-3">Oppetid: {formatUptime(instance.uptime_seconds)}</span>
										{/if}
									</p>
								</div>
							</div>
							{#if error}
								<p class="text-xs text-red-400">{error}</p>
							{/if}
						</div>
					</div>

					<div class="grid md:grid-cols-2 gap-6">
						<!-- Card 2: Quick Settings -->
						<div class="p-6 rounded-xl bg-surface border border-border">
							<h3 class="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">
								Hurtiginnstillinger
							</h3>
							<div class="space-y-4">
								<div class="flex items-center justify-between">
									<div>
										<div class="text-sm font-medium">AI-modell</div>
										<div class="text-xs text-text-muted mt-0.5">
											{instance.container_name || 'Ikke konfigurert'}
										</div>
									</div>
									<button
										disabled
										class="px-3 py-1.5 text-xs text-text-muted border border-border rounded-lg cursor-not-allowed opacity-50"
										title="Kommer snart"
									>
										Endre
									</button>
								</div>
								<div class="h-px bg-border"></div>
								<div class="flex items-center justify-between">
									<div>
										<div class="text-sm font-medium">Personlighet</div>
										<div class="text-xs text-text-muted mt-0.5">Standard</div>
									</div>
									<button
										disabled
										class="px-3 py-1.5 text-xs text-text-muted border border-border rounded-lg cursor-not-allowed opacity-50"
										title="Kommer snart"
									>
										Endre
									</button>
								</div>
								<div class="h-px bg-border"></div>
								<div class="flex items-center justify-between">
									<div>
										<div class="text-sm font-medium">Opprettet</div>
										<div class="text-xs text-text-muted mt-0.5">
											{instance.created_at
												? new Date(instance.created_at).toLocaleDateString('nb-NO', {
														day: 'numeric',
														month: 'long',
														year: 'numeric'
													})
												: '—'}
										</div>
									</div>
								</div>
							</div>
						</div>

						<!-- Card 3: Actions -->
						<div class="p-6 rounded-xl bg-surface border border-border">
							<h3 class="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">
								Handlinger
							</h3>
							<div class="space-y-3">
								<button
									onclick={restart}
									disabled={restarting}
									class="w-full flex items-center justify-center gap-2 px-4 py-3 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white font-medium rounded-lg transition-colors text-sm"
								>
									{#if restarting}
										<svg
											class="animate-spin w-4 h-4"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
										>
											<circle
												class="opacity-25"
												cx="12"
												cy="12"
												r="10"
												stroke="currentColor"
												stroke-width="4"
											></circle>
											<path
												class="opacity-75"
												fill="currentColor"
												d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
											></path>
										</svg>
										Restarter...
									{:else}
										🔄 Restart bot
									{/if}
								</button>
								<button
									onclick={() => (showDeleteModal = true)}
									class="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-600/30 font-medium rounded-lg transition-colors text-sm"
								>
									🗑️ Slett instans
								</button>
							</div>
						</div>
					</div>

					<!-- Card 4: Log placeholder -->
					<div class="p-6 rounded-xl bg-surface border border-border">
						<h3 class="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">
							📋 Logg
						</h3>
						<p class="text-sm text-text-muted">
							Samtalelogg og aktivitetshistorikk kommer snart. Her vil du kunne se meldinger, feil
							og hendelser fra boten din.
						</p>
					</div>
				</div>
			{/if}
		</main>
	</div>

	<!-- Delete confirmation modal -->
	{#if showDeleteModal}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center p-6"
			role="dialog"
			aria-modal="true"
		>
			<!-- Backdrop -->
			<button
				class="absolute inset-0 bg-black/60 cursor-default"
				onclick={() => (showDeleteModal = false)}
				aria-label="Lukk"
			></button>
			<!-- Dialog -->
			<div class="relative w-full max-w-md p-6 rounded-xl bg-surface border border-border">
				<h3 class="text-lg font-semibold mb-2">Slett instans?</h3>
				<p class="text-sm text-text-muted mb-6">
					Dette vil stoppe boten og slette all data permanent. Denne handlingen kan ikke angres.
				</p>
				<div class="flex items-center gap-3 justify-end">
					<button
						onclick={() => (showDeleteModal = false)}
						class="px-4 py-2 text-sm text-text-muted hover:text-text transition-colors"
					>
						Avbryt
					</button>
					<button
						onclick={deleteInstance}
						disabled={deleting}
						class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors text-sm"
					>
						{deleting ? 'Sletter...' : 'Ja, slett permanent'}
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}
