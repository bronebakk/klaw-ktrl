import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const PROVISIONING_API = process.env.PROVISIONING_API_URL ?? 'http://localhost:8100';
const PROVISIONING_API_KEY = process.env.PROVISIONING_API_KEY ?? 'dev-secret-key-change-me';

export const POST: RequestHandler = async ({ params }) => {
	const resp = await fetch(`${PROVISIONING_API}/api/instances/${params.user_id}/restart`, {
		method: 'POST',
		headers: { 'X-API-Key': PROVISIONING_API_KEY }
	});
	const data = await resp.json();
	return json(data, { status: resp.status });
};
