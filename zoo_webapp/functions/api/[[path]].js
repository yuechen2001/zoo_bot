export async function onRequest({ request, env, params }) {
  const url = new URL(request.url)
  const apiPath = '/api/' + (params.path || []).join('/')
  const targetUrl = 'http://' + env.VM_IP + ':8000' + apiPath + url.search

  const headers = new Headers(request.headers)
  if (env.API_SECRET) {
    headers.set('X-Internal-API-Key', env.API_SECRET)
  }
  headers.delete('host')

  const init = { method: request.method, headers }
  if (!['GET', 'HEAD'].includes(request.method)) {
    init.body = request.body
  }

  return fetch(targetUrl, init)
}
