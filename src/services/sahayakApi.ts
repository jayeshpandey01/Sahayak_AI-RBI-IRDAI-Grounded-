import {apiClient, authHeaders} from './apiClient';

export type LenderOffer = {
  offer_id: string;
  lender_id: string;
  lender_name: string;
  min_amount: number;
  max_amount: number;
  min_tenure_months: number;
  max_tenure_months: number;
  annual_interest_rate_percent: number;
  disclaimer?: string;
  product_name?: string;
  loan_type?: string;
  min_monthly_income?: number | null;
  employment_types?: string[];
  locations?: string[];
  source_name?: string | null;
  source_url?: string | null;
  source_type?: 'synthetic' | 'official' | 'partner';
  last_verified_at?: string | null;
  eligibility_data_missing?: boolean;
  missing_criteria?: string[];
};

export async function getOffers(
  token: string,
  criteria?: {
    loan_amount?: number;
    tenure_months?: number;
    monthly_income?: number;
    employment_type?: string;
    location?: string;
  },
): Promise<LenderOffer[]> {
  const {data} = await apiClient.get('/api/financial/offers', {
    headers: authHeaders(token),
    params: criteria,
  });
  return data;
}

export async function calculateEmi(
  token: string,
  input: {
    loan_amount: number;
    tenure_months: number;
    offer_id: string;
    maximum_emi?: number;
  },
) {
  const {data} = await apiClient.post('/api/financial/calculate', input, {
    headers: authHeaders(token),
  });
  return data;
}

export async function createJourney(
  token: string,
  input: {
    loan_amount: number;
    preferred_tenure_months: number;
    purpose: string;
    language: string;
  },
) {
  const {data} = await apiClient.post(
    '/api/journeys',
    input,
    mutationConfig(token),
  );
  return data;
}

export async function getJourney(token: string, journeyId: string) {
  const {data} = await apiClient.get(`/api/journeys/${journeyId}`, {
    headers: authHeaders(token),
  });
  return data;
}

export async function getLoanReadinessHistory(token: string) {
  const {data} = await apiClient.get('/api/journeys', {
    headers: authHeaders(token),
  });
  return data as Array<{
    id: string;
    stage: string;
    loan_amount: number;
    purpose: string;
    preferred_tenure_months: number;
    ready_for_handoff: boolean;
    updated_at: string;
  }>;
}

export async function reviseJourney(
  token: string,
  journeyId: string,
  input: {
    loan_amount: number;
    preferred_tenure_months: number;
    purpose: string;
    language: string;
  },
) {
  const {data} = await apiClient.patch(
    `/api/journeys/${journeyId}/revise`,
    input,
    mutationConfig(token),
  );
  return data;
}

export async function updateJourneyStage(
  token: string,
  journeyId: string,
  input: {
    stage: string;
    customer_confirmed: boolean;
    selected_offer_id?: string;
  },
) {
  const {data} = await apiClient.patch(
    `/api/journeys/${journeyId}/stage`,
    input,
    mutationConfig(token),
  );
  return data;
}

export async function recordConsent(
  token: string,
  journeyId: string,
  input: {scope: string; purpose: string; is_granted: boolean},
) {
  const {data} = await apiClient.post(
    `/api/journeys/${journeyId}/consent`,
    input,
    mutationConfig(token),
  );
  return data;
}

export async function uploadSyntheticDocument(
  token: string,
  journeyId: string,
  documentType: string,
) {
  const {data} = await apiClient.post(
    `/api/journeys/${journeyId}/documents/upload`,
    {
      document_type: documentType,
      simulate_quality_flag: 'normal',
      raw_text: '',
    },
    mutationConfig(token),
  );
  return data;
}

export async function confirmDocument(
  token: string,
  journeyId: string,
  documentId: string,
  fields: Record<string, string>,
) {
  const {data} = await apiClient.post(
    `/api/journeys/${journeyId}/documents/${documentId}/confirm`,
    {confirmed_fields: fields},
    mutationConfig(token),
  );
  return data;
}

export async function sendChatMessage(
  token: string,
  input: {
    message: string;
    journey_id?: string;
    language: string;
    allow_external_processing?: boolean;
    payment_order_id?: string;
    include_payment_context?: boolean;
    include_audio?: boolean;
    conversation?: Array<{role: string; content: string}>;
  },
) {
  const {data} = await apiClient.post(
    '/api/chat',
    {
      ...input,
      allow_external_processing: input.allow_external_processing ?? true,
      include_payment_context: input.include_payment_context ?? false,
    },
    {headers: authHeaders(token)},
  );
  return data;
}

export async function createStripeWalletTopup(
  token: string,
  amountRupees: number,
  idempotencyKey: string,
) {
  const {data} = await apiClient.post(
    '/api/v1/wallet/payment-orders',
    {
      amount_rupees: amountRupees,
      currency: 'inr',
      purpose: 'wallet_topup',
    },
    {headers: {...authHeaders(token), 'X-Idempotency-Key': idempotencyKey}},
  );
  return data as {
    order_id: string;
    amount_paise: number;
    status: string;
    provider: string;
    checkout_url: string;
  };
}

export async function refreshStripeWalletTopup(token: string, orderId: string) {
  const {data} = await apiClient.get(
    `/api/v1/wallet/payment-orders/${encodeURIComponent(orderId)}`,
    {headers: authHeaders(token)},
  );
  return data as {
    order_id: string;
    amount_paise: number;
    status: string;
    provider: string;
  };
}

export async function getServerWalletBalance(token: string) {
  const {data} = await apiClient.get('/api/v1/wallet/balance', {
    headers: authHeaders(token),
  });
  return data as {
    balance_paise: number;
    credited_total_paise: number;
    currency: string;
    ledger_entries: Array<{
      payment_order_id: string;
      amount_paise: number;
      currency: string;
      created_at: string;
    }>;
  };
}

export type DemoWalletInfo = {
  wallet_code: string;
  display_name: string;
  balance_paise: number;
  currency: 'INR';
  is_simulation: true;
};

export type DemoWalletEntry = {
  transaction_id: string;
  entry_type: 'DEMO_FUND' | 'CREDIT' | 'DEBIT';
  amount_paise: number;
  currency: 'INR';
  description: string;
  counterparty_name?: string | null;
  created_at: string;
  is_simulation: true;
};

export async function getDemoWallet(token: string) {
  const {data} = await apiClient.get('/api/v1/demo-wallet/me', {
    headers: authHeaders(token),
  });
  return data as DemoWalletInfo;
}

export async function getDemoWalletEntries(token: string, limit = 100) {
  const {data} = await apiClient.get('/api/v1/demo-wallet/entries', {
    headers: authHeaders(token),
    params: {limit},
  });
  return data as DemoWalletEntry[];
}

export async function addDemoWalletFunds(
  token: string,
  amountRupees: number,
  idempotencyKey: string,
) {
  const {data} = await apiClient.post(
    '/api/v1/demo-wallet/funds',
    {amount_rupees: amountRupees},
    {headers: {...authHeaders(token), 'X-Idempotency-Key': idempotencyKey}},
  );
  return data as {
    transaction_id: string;
    amount_paise: number;
    balance_paise: number;
    status: string;
    is_simulation: true;
  };
}

export async function sendDemoWalletFunds(
  token: string,
  input: {recipient_wallet_code: string; amount_rupees: number; note?: string},
  idempotencyKey: string,
) {
  const {data} = await apiClient.post('/api/v1/demo-wallet/transfers', input, {
    headers: {...authHeaders(token), 'X-Idempotency-Key': idempotencyKey},
  });
  return data as {
    transaction_id: string;
    amount_paise: number;
    balance_paise: number;
    recipient_name: string;
    status: string;
    is_simulation: true;
  };
}

export function parseDemoWalletQr(value: string): string | null {
  const match = value
    .trim()
    .match(/^ubanku-demo:\/\/pay\?code=([A-Z0-9-]{8,24})$/i);
  return match?.[1]?.toUpperCase() || null;
}

export type PaymentBehaviourEstimate = {
  score_type: 'sahayak_demo_payment_behaviour';
  is_official_credit_score: false;
  status: 'INSUFFICIENT_DATA' | 'ESTIMATE_AVAILABLE';
  score: number | null;
  range: {min: number; max: number} | null;
  repayment_count: number;
  on_time_count: number;
  late_count: number;
  missed_count: number;
  basis: string;
  disclaimer: string;
  calculated_at: string;
};

export async function getPaymentBehaviourEstimate(token: string) {
  const {data} = await apiClient.get(
    '/api/v1/credit-profile/payment-behaviour',
    {headers: authHeaders(token)},
  );
  return data as PaymentBehaviourEstimate;
}

export type WalletPaymentHistoryItem = {
  order_id: string;
  status: string;
  purpose: string;
  amount_rupees: number | string;
  currency: string;
  provider: string;
  reference_id?: string | null;
  created_at: string;
  updated_at: string;
};

export async function getWalletPaymentHistory(token: string) {
  const {data} = await apiClient.get('/api/v1/wallet/payment-orders', {
    headers: authHeaders(token),
  });
  return data as WalletPaymentHistoryItem[];
}

export async function recordPaymentContextAIConsent(
  token: string,
  isGranted: boolean,
) {
  const {data} = await apiClient.post(
    '/api/v1/payments/ai-context-consent',
    {is_granted: isGranted},
    {headers: authHeaders(token)},
  );
  return data;
}

// ----------------- MULTI-PLATFORM LOAN & EMI AUDIT API -----------------

export type LenderType = 'BANK' | 'NBFC' | 'FINTECH';
export type LoanType =
  | 'PERSONAL'
  | 'HOME'
  | 'AUTO'
  | 'EDUCATION'
  | 'CONSUMER_DURABLE'
  | 'CREDIT_LINE'
  | 'GOLD';
export type LoanStatus = 'ACTIVE' | 'OVERDUE' | 'CLOSED' | 'RESTRUCTURED';

export interface UserLoan {
  id: string;
  user_id: string;
  lender_name: string;
  lender_type: LenderType;
  loan_type: LoanType;
  account_number: string;
  original_principal: number;
  outstanding_principal: number;
  interest_rate_percent: number;
  tenure_months: number;
  remaining_tenure_months: number;
  emi_amount: number;
  emi_due_day: number;
  next_due_date: string;
  status: LoanStatus;
  disbursement_date?: string;
  processing_fee_paid: number;
  prepayment_penalty_percent: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PrepaymentSimulationResult {
  target_loan_id: string;
  lender_name: string;
  simulation_mode: 'EXTRA_MONTHLY' | 'LUMP_SUM';
  prepayment_amount: number;
  original_tenure_remaining_months: number;
  new_tenure_remaining_months: number;
  months_saved: number;
  original_remaining_interest: number;
  new_remaining_interest: number;
  interest_saved_rupees: number;
  advice: string;
}

export interface RefinanceOpportunity {
  loan_id: string;
  lender_name: string;
  loan_type: string;
  outstanding_principal: number;
  current_interest_rate: number;
  catalogue_offer_lender: string;
  catalogue_offer_rate: number;
  monthly_saving_rupees: number;
  lifetime_saving_rupees: number;
  processing_fee_estimate: number;
  net_benefit_rupees: number;
  is_worthwhile: boolean;
  recommendation: string;
}

export interface EMICalendarItem {
  loan_id: string;
  lender_name: string;
  loan_type: string;
  account_number: string;
  emi_amount: number;
  due_day: number;
  next_due_date: string;
  days_until_due: number;
  status: string;
}

export interface LoanAuditReport {
  total_loans_count: number;
  active_loans_count: number;
  total_borrowed_principal: number;
  total_outstanding_principal: number;
  total_monthly_emi: number;
  total_remaining_interest: number;
  weighted_average_interest_rate: number;
  monthly_income: number;
  foir_percent: number;
  foir_risk_level: 'SAFE' | 'MODERATE' | 'HIGH_RISK' | 'CRITICAL';
  foir_advice: string;
  high_interest_loans_count: number;
  total_monthly_interest_leakage: number;
  refinancing_opportunities: RefinanceOpportunity[];
  prepayment_simulation?: PrepaymentSimulationResult;
  emi_calendar: EMICalendarItem[];
  ai_insights: string[];
  action_plan: string[];
  rbi_guideline_notes: string[];
  generated_at: string;
}

export async function getUserLoans(
  token: string,
  statusFilter?: string,
): Promise<UserLoan[]> {
  const {data} = await apiClient.get('/api/loans', {
    headers: authHeaders(token),
    params: statusFilter ? {status_filter: statusFilter} : undefined,
  });
  return data;
}

export async function createUserLoan(
  token: string,
  payload: Partial<UserLoan>,
): Promise<UserLoan> {
  const config = mutationConfig(token);
  const {data} = await apiClient.post('/api/loans', payload, config);
  return data;
}

export async function updateUserLoan(
  token: string,
  loanId: string,
  payload: Partial<UserLoan>,
): Promise<UserLoan> {
  const config = mutationConfig(token);
  const {data} = await apiClient.put(`/api/loans/${loanId}`, payload, config);
  return data;
}

export async function deleteUserLoan(
  token: string,
  loanId: string,
): Promise<{success: boolean}> {
  const config = mutationConfig(token);
  const {data} = await apiClient.delete(`/api/loans/${loanId}`, config);
  return data;
}

export async function seedDemoLoans(token: string): Promise<UserLoan[]> {
  const config = mutationConfig(token);
  const {data} = await apiClient.post('/api/loans/seed-demo', {}, config);
  return data;
}

export async function runLoanAudit(
  token: string,
  payload?: {
    monthly_income?: number;
    extra_monthly_prepayment?: number;
    lump_sum_prepayment?: number;
    target_loan_id?: string;
  },
): Promise<LoanAuditReport> {
  const headers = authHeaders(token);
  const {data} = await apiClient.post('/api/loans/audit', payload || {}, {
    headers,
  });
  return data;
}

export async function simulatePrepayment(
  token: string,
  payload?: {
    target_loan_id?: string;
    extra_monthly_prepayment?: number;
    lump_sum_prepayment?: number;
  },
): Promise<PrepaymentSimulationResult> {
  const headers = authHeaders(token);
  const {data} = await apiClient.post(
    '/api/loans/simulate-prepayment',
    payload || {},
    {headers},
  );
  return data;
}

export async function getRefinanceOpportunities(
  token: string,
): Promise<RefinanceOpportunity[]> {
  const headers = authHeaders(token);
  const {data} = await apiClient.get('/api/loans/refinance-opportunities', {
    headers,
  });
  return data;
}

export type BillCategory =
  | 'ELECTRICITY' | 'RENT' | 'WATER' | 'GAS' | 'INTERNET'
  | 'MOBILE' | 'INSURANCE' | 'SUBSCRIPTION' | 'OTHER';
export type BillFrequency = 'WEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY';
export type RecurringBill = {
  id: string;
  name: string;
  category: BillCategory;
  payee?: string | null;
  expected_amount_rupees?: number | null;
  frequency: BillFrequency;
  next_due_date: string;
  reminder_days_before: number;
  is_active: boolean;
  notes?: string | null;
  due_status: 'PAUSED' | 'OVERDUE' | 'DUE_TODAY' | 'DUE_SOON' | 'UPCOMING';
  days_until_due: number;
  created_at: string;
  updated_at: string;
};
export type BillPaymentRecord = {
  id: string;
  bill_id: string;
  bill_name: string;
  due_date: string;
  amount_rupees: number;
  paid_at: string;
  note?: string | null;
};

export async function getRecurringBills(token: string, includeInactive = false): Promise<RecurringBill[]> {
  const {data} = await apiClient.get('/api/bills', {
    headers: authHeaders(token),
    params: includeInactive ? {include_inactive: true} : undefined,
  });
  return data;
}

export async function createRecurringBill(
  token: string,
  payload: {
    name: string;
    category: BillCategory;
    payee?: string;
    expected_amount_rupees?: number;
    frequency: BillFrequency;
    next_due_date: string;
    reminder_days_before: number;
    notes?: string;
  },
): Promise<RecurringBill> {
  const {data} = await apiClient.post('/api/bills', payload, mutationConfig(token));
  return data;
}

export async function updateRecurringBill(
  token: string,
  billId: string,
  payload: Partial<Pick<RecurringBill, 'is_active' | 'next_due_date' | 'expected_amount_rupees' | 'reminder_days_before'>>,
): Promise<RecurringBill> {
  const {data} = await apiClient.patch(`/api/bills/${billId}`, payload, mutationConfig(token));
  return data;
}

export async function recordBillPayment(
  token: string,
  billId: string,
  payload: {amount_rupees?: number; note?: string},
): Promise<BillPaymentRecord> {
  const {data} = await apiClient.post(`/api/bills/${billId}/payments`, payload, mutationConfig(token));
  return data;
}

export async function getBillPaymentHistory(token: string): Promise<BillPaymentRecord[]> {
  const {data} = await apiClient.get('/api/bills/payments/history', {
    headers: authHeaders(token),
  });
  return data;
}

function mutationConfig(token: string) {
  return {
    headers: {
      ...authHeaders(token),
      'X-Idempotency-Key': `mobile-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 10)}`,
    },
  };
}
