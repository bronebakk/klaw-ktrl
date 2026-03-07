import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const PROVISIONING_API = process.env.PROVISIONING_API_URL ?? 'http://localhost:8100';

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();

	const resp = await fetch(`${PROVISIONING_API}/api/validate/telegram-token`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	const data = await resp.json();
	return json(data, { status: resp.status });
};
