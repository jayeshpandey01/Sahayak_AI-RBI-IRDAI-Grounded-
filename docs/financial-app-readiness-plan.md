# Paytm-style Sahayak app: current readiness and delivery plan

The product can use a Paytm-like navigation and feature set while retaining Sahayak branding. That does not mean a Stripe account alone can provide all payment, wallet, P2P, merchant collection, or lending functions. This document records the current code boundary and prerequisites for a real end-to-end release.

## What is connected now

| Capability | Current implementation | Status |
| --- | --- | --- |
| Sign in/register | Email/password FastAPI auth, JWT session validation | Demo connected |
| Demo wallet balance | Dedicated account-scoped demo ledger with server-side balance | Simulated funds only; no cash value or withdrawals |
| Stripe wallet top-up | Authenticated Stripe Checkout order, webhook status and one-time credit | Test path; separate from demo wallet and not spendable by demo transfers |
| Wallet top-up | Authenticated Stripe Checkout order, webhook status and one-time credit | Test path; no live use without explicit approval |
| Payment history | Authenticated wallet order list with status and amount | Top-up history only; no UPI, merchant, P2P or bank ledger |
| Loan journey | Synthetic offer/EMI, synthetic documents, readiness stage/handoff | Not a loan application, approval, or disbursement |
| Loan readiness history | Authenticated list of user-owned journeys | Not an issued-loan account or repayment history |
| Multi-platform loan examples | Three account-scoped sample rows across a bank, NBFC and fintech, with `SIMULATED DEMO DATA ONLY` notes | Illustrative records only; not verified accounts, lender offers, or borrower obligations |
| Demo send/receive | QR-addressed transfer between signed-in demo wallets; server atomically debits sender and credits recipient | Simulated only; no Stripe call, actual transfer, payout, or withdrawal |
| Loan payments | No lender account, schedule or authoritative repayment endpoint | Not implemented |

## Required partners and product decisions

1. **Payment collection and wallet:** Decide whether funds are collected as merchant payments or held as stored value. Obtain a provider/partner contract and the required Indian payment aggregator/PPI arrangements for the exact flows. A general-purpose stored wallet needs the relevant authorization/partner model. Confirm provider sandbox, supported channels, refunds, disputes, settlement reporting, callbacks and idempotency.
2. **Stripe boundary:** Current Stripe India support does not include UPI and Stripe's India restricted-business rules cover lending, money transmission and stored-value use. Use only test mode for this demonstration unless Stripe explicitly approves the exact business model in writing. `STRIPE_FINANCIAL_SERVICES_APPROVED` is an operational fail-closed flag, not a legal or provider approval.
3. **Lending:** Select a regulated bank/NBFC (the regulated entity, or RE) and sign the required lender/LSP agreement. Obtain sandbox APIs for consent/KFS, creditworthiness decisioning, application state, disbursal status, repayment schedule, repayment initiation, reversals, complaints and reconciliation. Do not manufacture approvals or disbursals in the app.
4. **History:** Treat provider/lender events and server-side records as sources of truth. Store payment order state transitions and loan account/schedule/repayment events with ownership controls, audit trail and deduplication. A readiness journey must not be shown as an approved loan.

### Stripe send/receive decision

Stripe currently handles only the separate test top-up path. QR send/receive is available only between simulated demo accounts; withdrawal and payout are unavailable. Stripe Connect is not a general peer-to-peer transfer or cash-out API: it is for approved platform/marketplace funds flows, and India's connected-account onboarding is invite-only and use-case limited. Stripe's published policy lists P2P money transmission and digital wallets among unsupported financial-services categories. Do not turn on real transfers because Stripe credentials are configured. For the research, approval gates and conditional Connect plan, see [Stripe money-movement research and implementation plan](stripe-money-movement-research-plan.md).

The next product decision is whether “collect” means (a) the app selling its own service, (b) a marketplace buyer paying an onboarded seller, or (c) a user-to-user wallet/UPI transfer. Only (a) is ordinary merchant checkout; (b) requires Stripe's written Connect eligibility for this exact India platform and flow; (c) needs a separately approved Indian payment/wallet partner, not Stripe as a wallet funding shim.

**Demo data is allowed as simulation, not as a substitute for settlement.** We can persist synthetic loan accounts, EMI schedules, simulated payments and activity in the app database if every screen/API labels these as `simulated` and never describes them as received, paid, disbursed, withdrawable or legally owed. For a demo wallet, prefer database-only simulated credits and do not charge real cards for a balance users cannot actually spend or redeem. For a real merchant purchase, Stripe processes the charge and the database stores the corresponding order and webhook-verified result. For a real loan/EMI, the regulated lender/payment partner is authoritative; the database mirrors its verified IDs and state.

Stripe's current [India marketplace guidance](https://support.stripe.com/questions/stripe-india-support-for-marketplaces) says separate charges and transfers are not currently supported for Indian platforms, while manual payouts are only available for limited use cases. See the [feature matrix and research plan](stripe-money-movement-research-plan.md) before designing payment collection or history.

### Credit score demonstration

The app exposes an authenticated `/api/v1/credit-profile/payment-behaviour` summary and deterministic chat answer for questions like “what is my CIBIL score?”. This is explicitly **not CIBIL**: it is based only on rows in `demo_repayments` marked as simulation, and wallet top-ups are excluded. As there are currently no simulated repayment rows or bureau integration, the correct result is `INSUFFICIENT_DATA` and the chat says an official score is unavailable. CIBIL says its score/report is based on bureau credit history reported by banks and financial institutions, including repayment history and other account/enquiry factors; do not infer it from wallet activity. See [CIBIL score/report details](https://www.cibil.com/faq-brochure).

RBI Digital Lending Directions require the RE to retain responsibility and set requirements around offers/disclosures, creditworthiness assessment, KFS, consent, disbursal and repayment. See [RBI Digital Lending Directions, 2025](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12848&Mode=0). For stored-value/PPI authorization see [RBI's PPI Master Directions](https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12156%283%29.html). Stripe's current policy references are in the [Stripe integration status](stripe-migration-plan.md).

## Implementation order

### Phase 1 — safe demo and accurate state (in progress)

- Keep all payment credentials server-side and all live financial use disabled until approvals and partner selection.
- Make payment history owner-authenticated; do not return client secrets in history.
- Provide a user-owned loan-readiness history endpoint, label the records as readiness only, and retain synthetic/offline labels in screens.
- Keep send, withdraw and collect buttons visibly in demo state until they invoke a provider-authorized flow.
- Remove fabricated transaction rows and hard-coded financial totals wherever they imply real account history.

### Phase 2 — provider-neutral payment collection

- Add a backend provider interface (`create`, `fetch/verify`, `refund`, webhook verification) and canonical order/state model.
- Integrate the selected provider's sandbox; do not model collect/UPI intent flows as Stripe Checkout.
- Add merchant QR/collect and payer flows only for provider methods enabled on the merchant account.
- Add refunds, disputes, settlement reconciliation and complete activity ledger before declaring payment history complete.
- Acceptance: authenticated users can pay a sandbox merchant, collect in sandbox only where approved, view pending/success/failure/refund states, and cannot access other users' records; duplicate callbacks never double-post.

### Phase 3 — regulated lender integration

- Add lender adapter and consented application submission; send only fields required by the selected RE.
- Render lender-provided offers and required APR/fees/tenure/KFS disclosures without altering the terms.
- Persist lender application ID/status separately from Sahayak readiness; support lender-side rejection, withdrawal, cancellation and re-application.
- Add loan account, schedule and repayment entities only from lender-authoritative data. Repayment actions must use the lender-approved route and never credit the app wallet.
- Acceptance: no loan shown as active until lender confirms; every payment reconciles with lender and provider; audit logs retain consent, status transitions and traceable references.

### Phase 4 — production verification

- Deploy with PostgreSQL, migrations, secrets manager, TLS, backups, monitoring and incident procedures.
- Complete security/privacy, authorization, idempotency, webhook replay, concurrency and mobile interruption testing.
- Run provider and lender sandbox end-to-end tests with synthetic accounts, then obtain written production enablement from every partner.
- Reconcile dashboard UI, provider/lender statements and backend records before production launch.

## Current limitations

- No production payment provider or lender contract/API credentials are established in the repository.
- Stripe Checkout/webhook has not been verified against the configured account in this environment; test credentials were not used to perform a real transaction.
- The app has no real loan account, disbursement, repayment schedule, EMI repayment, P2P transfer, merchant QR/collect, refund, or dispute workflow.
- SQLite and current synthetic offers/OCR are suitable for local demonstration, not production financial recordkeeping.
