export type LocationOption = {
  id: string
  code: 'BACKROOM' | 'SALES_SHELF'
}

export type AuditScopeType = 'SELECTED_PAIRS' | 'WHOLE_WAREHOUSE'

export type AuditContextPair = {
  sku_id: string
  sku: string
  location_id: string
  location: 'BACKROOM' | 'SALES_SHELF'
  preview_system_quantity: number
}

export type AuditContext = {
  warehouse_id: string
  pairs: AuditContextPair[]
}

export type AuditCommand = {
  scope_type: AuditScopeType
  lines: Array<{
    sku_id: string
    location_id: string
    physical_quantity: number
  }>
}

export type AuditResult = {
  audit_id: string
  warehouse_id: string
  scope_type: AuditScopeType
  result: 'MATCH' | 'MISMATCH'
  status: 'MATCH_COMPLETED' | 'MISMATCH_RECORDED'
  audited_by_user_id: string
  audited_at: string
  lines: Array<{
    sku_id: string
    location_id: string
    system_quantity: number
    physical_quantity: number
    quantity_discrepancy: number
    result: 'MATCH' | 'MISMATCH'
  }>
}

export type AuditDiscrepancyActor = {
  user_id: string
  login_identifier: string
}

export type AuditRecheckEvidence = {
  recheck_id: string
  recheck_system_quantity: number
  recheck_physical_quantity: number
  recheck_quantity_discrepancy: number
  result: 'MATCH' | 'MISMATCH'
  performed_by: AuditDiscrepancyActor
  performed_at: string
}

export type AuditDiscrepancy = {
  audit_id: string
  audit_line_id: string
  warehouse_id: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  original: {
    system_quantity: number
    physical_quantity: number
    quantity_discrepancy: number
    result: 'MISMATCH'
    audited_by: AuditDiscrepancyActor
    audited_at: string
  }
  recheck: AuditRecheckEvidence | null
  adjust_eligible: boolean
}

export type AuditDiscrepancyList = {
  items: AuditDiscrepancy[]
}

export type AuditRecheckResult = AuditRecheckEvidence & {
  audit_line_id: string
  adjust_eligible: boolean
}

export type AdjustmentActor = {
  user_id: string
  login_identifier: string
}

export type ExistingAdjustment = {
  adjustment_id: string
  reason: string
  requested_change: number
  status: AdjustmentStatus
  requested_by: AdjustmentActor
  requested_at: string
}

export type AdjustmentContext = {
  audit_recheck_id: string
  warehouse_id: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  original_audit: {
    audit_id: string
    audit_line_id: string
    system_quantity: number
    physical_quantity: number
    quantity_discrepancy: number
  }
  recheck: {
    recheck_system_quantity: number
    recheck_physical_quantity: number
    recheck_quantity_discrepancy: number
    result: 'MISMATCH'
    performed_at: string
  }
  requested_change: number
  existing_adjustment: ExistingAdjustment | null
}

export type EligibleAdjustmentRecheck = {
  audit_recheck_id: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  recheck_system_quantity: number
  recheck_physical_quantity: number
  requested_change: number
  rechecked_at: string
}

export type EligibleAdjustmentRecheckList = {
  items: EligibleAdjustmentRecheck[]
}

export type AdjustmentResult = {
  adjustment_id: string
  audit_recheck_id: string
  warehouse_id: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  recheck_system_quantity_snapshot: number
  recheck_physical_quantity_snapshot: number
  requested_change: number
  reason: string
  status: AdjustmentStatus
  requested_by: AdjustmentActor
  requested_at: string
}

export type AdjustmentStatus =
  | 'PENDING_MANAGER_DECISION'
  | 'APPLIED'
  | 'REJECTED'

export type AdjustmentQueueItem = {
  adjustment_id: string
  status: 'PENDING_MANAGER_DECISION'
  requested_by: AdjustmentActor
  requested_at: string
  reason: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  requested_change: number
}

export type AdjustmentQueue = { items: AdjustmentQueueItem[] }

export type AdjustmentDetail = {
  adjustment_id: string
  audit_recheck_id: string
  warehouse_id: string
  sku: { id: string; code: string }
  location: { id: string; code: string }
  original_audit: {
    audit_id: string
    audit_line_id: string
    system_quantity: number
    physical_quantity: number
    quantity_discrepancy: number
    result: 'MISMATCH'
    audited_by: AdjustmentActor
    audited_at: string
  }
  manager_recheck: {
    recheck_id: string
    recheck_system_quantity: number
    recheck_physical_quantity: number
    recheck_quantity_discrepancy: number
    result: 'MISMATCH'
    performed_by: AdjustmentActor
    performed_at: string
  }
  recheck_system_quantity_snapshot: number
  recheck_physical_quantity_snapshot: number
  requested_change: number
  reason: string
  requested_by: AdjustmentActor
  requested_at: string
  status: AdjustmentStatus
  decided_by: AdjustmentActor | null
  decided_at: string | null
  rejection_reason: string | null
  applied_stock_before: number | null
  applied_stock_after: number | null
}

export type AdjustmentDecisionCommand =
  | { decision: 'APPROVE' }
  | { decision: 'REJECT'; rejection_reason: string }

export type PutawayContext = {
  receive_line_id: string
  sku_id: string
  sku: string
  actual_quantity: number
  confirmed_quantity: number
  eligible_quantity: number
  locations: LocationOption[]
}

export type PutawayQueue = {
  items: Array<{
    receive_line_id: string
    receive_id: string
    expected_reference: string
    sku_id: string
    sku: string
    actual_quantity: number
    confirmed_quantity: number
    eligible_quantity: number
  }>
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

export type PickQueue = {
  items: Array<{
    pick_id: string
    sku_id: string
    sku: string
    requested_quantity: number
    available_quantity: number
  }>
}

export type SkuCatalog = {
  items: Array<{ sku_id: string; sku: string }>
}

export type PickRequestCreateResult = {
  pick_id: string
  warehouse_id: string
  sku_id: string
  sku: string
  requested_quantity: number
  outcome: null
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

export type TransferSelector = {
  items: Array<{
    sku_id: string
    sku: string
    locations: PickLocation[]
    warehouse_total: number
  }>
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

export type PreparedReceiveQueue = {
  items: Array<{
    receive_id: string
    warehouse_id: string
    expected_reference: string
    lines: Array<{
      sku_id: string
      sku: string
      expected_quantity: number
    }>
  }>
}

export type PreparedReceiveCreateCommand = {
  expected_reference: string
  lines: Array<{ sku_id: string; expected_quantity: number }>
}

export type PreparedReceiveCreateResult = {
  receive_id: string
  warehouse_id: string
  expected_reference: string
  recorded_at: null
  lines: Array<{
    receive_line_id: string
    sku_id: string
    sku: string
    expected_quantity: number
  }>
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

export function loadEligiblePutawayLines(): Promise<PutawayQueue> {
  return apiRequest<PutawayQueue>('/api/v1/putaways/eligible-lines')
}

export function loadAuditContext(): Promise<AuditContext> {
  return apiRequest<AuditContext>('/api/v1/audits/context')
}

export function submitAudit(
  command: AuditCommand,
  idempotencyKey: string,
): Promise<AuditResult> {
  return apiRequest<AuditResult>('/api/v1/audits', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(command),
  })
}

export function loadAuditDiscrepancies(): Promise<AuditDiscrepancyList> {
  return apiRequest<AuditDiscrepancyList>('/api/v1/audit-discrepancies')
}

export function loadAuditDiscrepancy(
  auditLineId: string,
): Promise<AuditDiscrepancy> {
  return apiRequest<AuditDiscrepancy>(
    `/api/v1/audit-discrepancies/${auditLineId}`,
  )
}

export function submitAuditRecheck(
  auditLineId: string,
  recheckPhysicalQuantity: number,
  idempotencyKey: string,
): Promise<AuditRecheckResult> {
  return apiRequest<AuditRecheckResult>(
    `/api/v1/audit-discrepancies/${auditLineId}/rechecks`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify({
        recheck_physical_quantity: recheckPhysicalQuantity,
      }),
    },
  )
}

export function loadAdjustmentContext(
  auditRecheckId: string,
): Promise<AdjustmentContext> {
  return apiRequest<AdjustmentContext>(
    `/api/v1/adjustments/context/${auditRecheckId}`,
  )
}

export function loadEligibleAdjustmentRechecks(): Promise<EligibleAdjustmentRecheckList> {
  return apiRequest<EligibleAdjustmentRecheckList>(
    '/api/v1/adjustments/eligible-rechecks',
  )
}

export function submitAdjustmentRequest(
  auditRecheckId: string,
  reason: string,
  idempotencyKey: string,
): Promise<AdjustmentResult> {
  return apiRequest<AdjustmentResult>('/api/v1/adjustments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ audit_recheck_id: auditRecheckId, reason }),
  })
}

export function loadPendingAdjustments(): Promise<AdjustmentQueue> {
  return apiRequest<AdjustmentQueue>(
    '/api/v1/adjustments?status=PENDING_MANAGER_DECISION',
  )
}

export function loadAdjustmentDetail(
  adjustmentId: string,
): Promise<AdjustmentDetail> {
  return apiRequest<AdjustmentDetail>(
    `/api/v1/adjustments/${encodeURIComponent(adjustmentId)}`,
  )
}

export function submitAdjustmentDecision(
  adjustmentId: string,
  command: AdjustmentDecisionCommand,
  idempotencyKey: string,
): Promise<AdjustmentDetail> {
  return apiRequest<AdjustmentDetail>(
    `/api/v1/adjustments/${encodeURIComponent(adjustmentId)}/decision`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify(command),
    },
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

export function loadActionablePicks(): Promise<PickQueue> {
  return apiRequest<PickQueue>('/api/v1/picks')
}

export function loadSkuCatalog(): Promise<SkuCatalog> {
  return apiRequest<SkuCatalog>('/api/v1/skus')
}

export function createPickRequest(
  skuId: string,
  requestedQuantity: number,
): Promise<PickRequestCreateResult> {
  return apiRequest<PickRequestCreateResult>(
    '/api/v1/picks/requests',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sku_id: skuId,
        requested_quantity: requestedQuantity,
      }),
    },
    201,
  )
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

export function loadTransferableSkus(): Promise<TransferSelector> {
  return apiRequest<TransferSelector>('/api/v1/transfers/eligible-skus')
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

export function loadPreparedReceives(): Promise<PreparedReceiveQueue> {
  return apiRequest<PreparedReceiveQueue>('/api/v1/receives')
}

export function createPreparedReceive(
  command: PreparedReceiveCreateCommand,
): Promise<PreparedReceiveCreateResult> {
  return apiRequest<PreparedReceiveCreateResult>(
    '/api/v1/receives/prepared',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    },
    201,
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
