export async function onRequest({ request, env, params }) {
  const url = new URL(request.url)
  const apiPath = '/api/' + (params.path || []).join('/')

  if (!env.VM_IP) {
    return new Response(JSON.stringify({ error: 'VM_IP env var not set in Pages' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // Cloudflare Workers block fetch to bare IPs; nip.io resolves IP-as-hostname
  const host = env.VM_IP.replace(/\./g, '-') + '.nip.io'
  const targetUrl = 'http://' + host + ':8080' + apiPath + url.search

  const headers = new Headers(request.headers)
  if (env.API_SECRET) {
    headers.set('X-Internal-API-Key', env.API_SECRET)
  }
  headers.delete('host')

  const init = { method: request.method, headers }
  if (!['GET', 'HEAD'].includes(request.method)) {
    init.body = request.body
  }

  try {
    return await fetch(targetUrl, init)
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message, targetUrl }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
