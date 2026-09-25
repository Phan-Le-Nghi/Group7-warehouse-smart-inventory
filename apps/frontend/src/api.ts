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

export type PickLocation = {
  id: string
  code: 'BACKROOM' | 'SALES_SHELF'
  available_quantity: number
}

export type PickContext = {
  pick_id: string
  warehouse_id: string
  sku_id: string
  sku: string
  requested_quantity: number
  outcome: 'FULLY_COMPLETED' | 'PARTIAL_INSUFFICIENT' | null
  locations: PickLocation[]
  warehouse_total: number
}

export type PickAllocationCommand = {
  source_location_id: string
  quantity: number
}

export type PickResult = {
  pick_id: string
  sku_id: string
  requested_quantity: number
  picked_quantity: number
  remaining_quantity: number
  outcome: 'FULLY_COMPLETED' | 'PARTIAL_INSUFFICIENT'
  allocations: Array<{
    source_location_id: string
    source_location: string
    quantity: number
    remaining_source_quantity: number
  }>
  confirmed_by_user_id: string
  confirmed_at: string
  warehouse_total: number
}

export type TransferContext = {
  warehouse_id: string
  sku_id: string
  sku: string
  locations: PickLocation[]
  warehouse_total: number
}

export type TransferCommand = {
  sku_id: string
  source_location_id: string
  destination_location_id: string
  quantity: number
}

export type TransferResult = TransferCommand & {
  transfer_id: string
  warehouse_id: string
  source_location: string
  destination_location: string
  transferred_by_user_id: string
  transferred_at: string
  stock: {
    source_quantity: number
    destination_quantity: number
    warehouse_total: number
  }
}

export type TransferHistoryItem = {
  transfer_id: string
  warehouse_id: string
  sku: { id: string; code: string }
  quantity: number
  source: { id: string; code: string }
  destination: { id: string; code: string }
  transferred_by: { user_id: string; login_identifier: string }
  transferred_at: string
}

export type TransferHistory = {
  items: TransferHistoryItem[]
}

export type ReceiveReference = {
  expected: string
  document: string | null
  match_status: 'REFERENCE_MATCH' | 'REFERENCE_MISMATCH' | null
  reviewed_by_user_id: string | null
  reviewed_at: string | null
}

export type ReceiveLine = {
  receive_line_id: string
  sku_id: string
  sku: string
  expected_quantity: number
  actual_quantity: number | null
  quantity_discrepancy: number | null
}

export type ReceiveContext = {
  receive_id: string
  warehouse_id: string
  reference: ReceiveReference
  recorded_at: string | null
  putaway_eligible: boolean
  lines: ReceiveLine[]
}

export type ReceiveRecordRequest = {
  receive_id: string
  document_reference: string
  lines: Array<{
    receive_line_id: string
    sku_id: string
    actual_quantity: number
  }>
}

export type ReferenceReviewResult = {
  receive_id: string
  match_status: 'REFERENCE_MISMATCH'
  reviewed_by_user_id: string
  reviewed_at: string
  putaway_eligible: boolean
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

export async function loadPickContext(pickId: string): Promise<PickContext> {
  return apiRequest<PickContext>(`/api/v1/picks/context/${pickId}`)
}

export async function submitPick(
  pickId: string,
  allocations: PickAllocationCommand[],
): Promise<PickResult> {
  return apiRequest<PickResult>(
    '/api/v1/picks',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pick_id: pickId, allocations }),
    },
    201,
  )
}

export async function loadTransferContext(
  skuId: string,
): Promise<TransferContext> {
  return apiRequest<TransferContext>(`/api/v1/transfers/context/${skuId}`)
}

export async function submitTransfer(
  command: TransferCommand,
  idempotencyKey: string,
): Promise<TransferResult> {
  return apiRequest<TransferResult>('/api/v1/transfers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(command),
  })
}

export function loadTransferHistory(): Promise<TransferHistory> {
  return apiRequest<TransferHistory>('/api/v1/transfers')
}

export async function loadReceiveContext(
  receiveId: string,
): Promise<ReceiveContext> {
  return apiRequest<ReceiveContext>(
    `/api/v1/receives/context/${receiveId}`,
  )
}

export async function recordReceive(
  command: ReceiveRecordRequest,
): Promise<ReceiveContext> {
  return apiRequest<ReceiveContext>(
    '/api/v1/receives',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    },
    201,
  )
}

export async function acknowledgeReferenceMismatch(
  receiveId: string,
): Promise<ReferenceReviewResult> {
  return apiRequest<ReferenceReviewResult>(
    `/api/v1/receives/${receiveId}/reference-review`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    },
    200,
  )
}
