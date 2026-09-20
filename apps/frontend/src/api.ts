export type LocationOption = {
  id: string
  code: 'BACKROOM' | 'SALES_SHELF'
}

export type PutawayContext = {
  receive_line_id: string
  sku_id: string
  sku: string
  actual_quantity: number
  confirmed_quantity: number
  eligible_quantity: number
  locations: LocationOption[]
}

export type PutawayResult = {
  putaway_id: string
  receive_line_id: string
  sku_id: string
  quantity: number
  destination_location_id: string
  destination_location: string
  confirmed_at: string
  stock: {
    destination_quantity: number
    warehouse_total: number
  }
}

type ErrorEnvelope = {
  error?: {
    code?: string
    message?: string
    details?: unknown
  }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  return typeof value === 'object' && value !== null && 'error' in value
}

function isJsonResponse(response: Response): boolean {
  const contentType = response.headers.get('Content-Type') ?? ''
  return contentType.split(';', 1)[0].trim().toLowerCase() === 'application/json'
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  if (!isJsonResponse(response)) return undefined
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  expectedStatus?: number,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: 'include',
  })
  const body = response.status === 204 ? undefined : await parseJsonResponse(response)
  if (!response.ok) {
    const error = isErrorEnvelope(body) ? body.error : undefined
    throw new ApiError(
      response.status,
      error?.code ?? 'REQUEST_FAILED',
      error?.message ?? 'The request could not be completed.',
      error?.details,
    )
  }
  if (expectedStatus !== undefined && response.status !== expectedStatus) {
    throw new ApiError(
      response.status,
      'UNEXPECTED_RESPONSE',
      'The server returned an unexpected response.',
    )
  }
  if (response.status === 204) return undefined as T
  if (body === undefined) {
    throw new ApiError(
      response.status,
      'INVALID_RESPONSE',
      'The server returned an invalid response.',
    )
  }
  return body as T
}

export async function loadPutawayContext(
  receiveLineId: string,
): Promise<PutawayContext> {
  return apiRequest<PutawayContext>(
    `/api/v1/putaways/context/${receiveLineId}`,
  )
}

export async function submitPutaway(
  context: PutawayContext,
  destinationLocationId: string,
  idempotencyKey: string,
): Promise<PutawayResult> {
  return apiRequest<PutawayResult>('/api/v1/putaways', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      receive_line_id: context.receive_line_id,
      sku_id: context.sku_id,
      quantity: context.eligible_quantity,
      destination_location_id: destinationLocationId,
    }),
  })
}
