<script>
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head>
	<title>Klaw — Din egen AI-assistent</title>
	<meta name="description" content="Sett opp din egen AI-assistent på 5 minutter. Koble til Telegram, velg AI-modell, og du er i gang." />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="min-h-screen bg-bg">
	{@render children()}
</div>
