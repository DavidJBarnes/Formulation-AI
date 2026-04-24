const TOKEN_KEY = 'formulation_ai_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

type FetchOptions = Omit<RequestInit, 'body'> & { body?: unknown }

export async function apiFetch<T = unknown>(path: string, options: FetchOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options
  const token = getToken()
  const finalHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...(headers as Record<string, string> | undefined),
  }
  if (token) finalHeaders.Authorization = `Bearer ${token}`

  let finalBody: BodyInit | undefined
  if (body instanceof FormData || body instanceof URLSearchParams) {
    finalBody = body
  } else if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json'
    finalBody = JSON.stringify(body)
  }

  const res = await fetch(`/api${path}`, { ...rest, headers: finalHeaders, body: finalBody })

  if (res.status === 401) {
    setToken(null)
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') detail = data.detail
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
