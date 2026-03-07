import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const PROVISIONING_API = process.env.PROVISIONING_API_URL ?? 'http://localhost:8100';
const PROVISIONING_API_KEY = process.env.PROVISIONING_API_KEY ?? 'dev-secret-key-change-me';

export const GET: RequestHandler = async ({ params }) => {
	const resp = await fetch(`${PROVISIONING_API}/api/instances/${params.user_id}`, {
		headers: { 'X-API-Key': PROVISIONING_API_KEY }
	});
	const data = await resp.json();
	return json(data, { status: resp.status });
};

export const DELETE: RequestHandler = async ({ params }) => {
	const resp = await fetch(
		`${PROVISIONING_API}/api/instances/${params.user_id}?keep_data=false`,
		{
			method: 'DELETE',
			headers: { 'X-API-Key': PROVISIONING_API_KEY }
		}
	);
	const data = await resp.json();
	return json(data, { status: resp.status });
};
