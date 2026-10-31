# Stripe money movement research and implementation plan

**Research date:** 2026-10-31  
**Product context:** Sahayak AI is an India-first, Paytm-style demo app. Stripe currently handles a test wallet top-up only. The request is to enable payment sending, receiving/collecting and activity history through Stripe.

## Executive recommendation

Do not turn on Stripe transfers or payouts for the current wallet. The app records test top-ups and separately provides an account-scoped demo wallet: demo funding is simulated, and QR-addressed demo sends debit one demo balance and credit another in the database. These demo records do not call Stripe or move real money; withdrawals remain unavailable. Stripe's India policy excludes local UPI/netbanking/EMI methods; Stripe's restricted-business policy and FAQ identify personal/P2P money transmission and digital wallets as unsupported financial-service categories. Stripe India accounts and new connected accounts are invite-only, and Connect onboarding in India is limited to certain use cases. Having API credentials is not evidence of account or use-case approval.

First decide which product is actually intended:

1. **Merchant checkout:** a customer pays the app operator for the operator's own product/service. This can be evaluated as a normal Stripe payment after confirming the business and payment methods are approved. It is not peer-to-peer transfer and does not create a reusable wallet balance.
2. **Marketplace collection and seller settlement:** a buyer purchases from a real, onboarded seller; an eligible Connect flow may route a related charge to that seller. Stripe must approve the platform, seller types, countries, charge model and funds flow. A Connect transfer is not a general-purpose remittance feature.
3. **P2P send / stored wallet / cash-out:** users fund an in-app balance, send it to one another, or withdraw it. Stripe's public policy indicates this is not an appropriate Stripe Payments/Connect use for this product. Do not build this on Stripe. Select a bank, authorized Indian PPI/payment partner, or other legally suitable rails after specialist regulatory review.

The app's stated Paytm-like scope includes wallet, send, collect/merchant payments, UPI and lending. Stripe alone cannot satisfy that scope. A sensible demo can keep Stripe hosted card checkout for a clearly labeled one-time demo/merchant payment, while a separate India payment partner handles any approved production UPI/wallet flow. A regulated lender must separately own real loan decisions, disbursal and repayment.

## Capability decision matrix: Stripe or demo database?

| App feature | Stripe use | Database/demo use | Recommended boundary |
| --- | --- | --- | --- |
| Pay for the app operator's own real product/service | Potentially Stripe Checkout/PaymentIntent for approved products and enabled methods | Persist order, provider IDs and verified status | Stripe handles the actual charge; DB is the auditable application record. This is not a wallet top-up. Confirm account/business eligibility first. |
| Pay an unrelated merchant / “collect” for a seller | Only through a Stripe-approved Connect arrangement; India platform restrictions apply | Store simulated merchant/pay events for a demo | No live seller transfer until Stripe explicitly confirms a supported India flow. Stripe currently says separate charges and transfers are unsupported for India platforms; manual connected-account payouts are limited-use and require contacting Support. |
| Add money to a reusable app wallet | Do not assume ordinary card checkout can fund a spendable wallet; Stripe policy identifies digital wallets and account funding among unsupported/restricted areas | Can persist a clearly simulated balance and events | Demo only: banner/status must say “simulation”; no cash value, redemption, transfer, or withdrawal. For real value, use an authorized PPI/bank/provider design. |
| P2P send, UPI transfer, cash-out | Do not use Stripe for this app's described flow | Can store simulated requests and outcomes only | For real transfers, integrate a provider and legal structure explicitly supporting those rails. A DB entry alone never moves funds. |
| Fake loan offer/application/loan account | Stripe does not issue loans | Persist a `simulated` loan and synthetic schedule for demo | Must clearly say no real credit decision, funds, borrower liability or lender account exists. |
| Real loan decision/disbursal | Stripe is not the lender and should not be used to represent disbursal | DB stores authoritative status received from a regulated lender | Integrate a bank/NBFC (regulated entity); lender remains source of truth. Never mark “disbursed” from an app-created row. |
| Simulated EMI paid | No Stripe charge for a fake EMI | Save a simulated EMI event and show “Demo — not paid” | Suitable only for product walkthroughs. Do not add it to a real loan balance or say the lender received money. |
| Real EMI repayment | Stripe India lists EMI as an unsupported local payment method; Stripe policy also restricts lending/financial-service use | Store a payment attempt and lender reconciliation result | Initiate through the lender-authorized repayment channel/provider. Credit repayment only after provider and lender confirmation. |
| Transaction/loan history | Stripe supplies provider payment events, not a complete bank statement or loan ledger | DB can unify real provider/lender events and clearly tagged simulations | Store source, environment, real/simulated flag, canonical status, owner, linked provider/lender reference, and timestamps. Never mix demo credits with real available funds. |
| CIBIL / bureau score | Do not synthesize or claim a bureau score from Stripe or wallet history | The demo may show a separately named behavior indicator from synthetic EMI records | A real CIBIL score/report must come from TransUnion CIBIL or an authorized data source with the user's valid consent. Payment top-ups are not CIBIL tradelines. |

For the current code, keep the existing Stripe integration on its explicitly limited top-up test path until the product owner decides whether it is just a non-transferable demo simulation or an approved merchant purchase. If it is a demo-only wallet balance, the safest design is to avoid taking real card money for it: use database simulation and disable Stripe checkout for that balance. If it represents real collected funds, get written Stripe approval for that exact use before accepting them.

## Verified repository state

| Area | Current evidence | Consequence |
| --- | --- | --- |
| Top-up creation | `backend/app/api/payment_orders.py` exposes authenticated wallet order routes; `backend/app/services/payment_service.py` creates Stripe payment orders and credits a ledger idempotently from verified provider state. | This is the only Stripe wallet money flow. Its current test/demo ledger must not be treated as redeemable funds. |
| Provider plumbing | `backend/app/services/stripe_service.py` creates Stripe PaymentIntents; Checkout flow and webhook configuration are documented in `docs/stripe-migration-plan.md`. | Existing code is not a Connect integration. |
| Demo send/receive | `backend/app/api/demo_wallet.py` and `demo_wallet_service.py` move simulated amounts between owned demo accounts through paired ledger rows; QR codes address demo wallet codes. | App database only. Stripe is not called; demo funds are not cash and cannot be withdrawn. |
| Stripe top-ups | Authenticated Stripe Checkout and webhook-confirmed credits remain available as a separate test path. | Stripe test credits are excluded from the demo wallet balance and cannot fund its sends. |
| Local wallet | `src/screens/HomeWallet.tsx` displays the demo balance and identifies Stripe test credits separately. | The demo wallet is internally spendable between demo accounts only; it is not a stored-value product. |
| History | Authenticated history is wallet order/top-up history. | It is not a complete payments, transfer, refund, dispute or bank statement. |
| Loans | `app.md` and `docs/financial-app-readiness-plan.md` describe synthetic readiness journeys, not lender-issued accounts. | Stripe must not be used to represent loan disbursal or repayment in this app. |
| Live gating | `backend/app/config.py` requires `STRIPE_FINANCIAL_SERVICES_APPROVED=true` for relevant live Stripe mode. | The environment flag is only a guardrail; it is not proof that Stripe or a regulator approved the use. |

## Provider and regulatory research

### Stripe

- Stripe says India accounts are invite-only; platforms in India can add new connected accounts by invite only. [Stripe India account availability](https://support.stripe.com/questions/stripe-accounts-are-invite-only-in-india)
- Stripe says India businesses do not have local methods such as UPI, netbanking, BNPL and EMI supported. [India payment methods](https://support.stripe.com/questions/supported-payment-methods-currencies-and-businesses-for-stripe-accounts-in-india?locale=en-GB)
- Stripe's restricted-business FAQ says it cannot support many financial-services businesses, including P2P money transmission and digital wallets. [Restricted-business FAQ](https://support.stripe.com/questions/prohibited-and-restricted-business-list-faqs)
- Stripe's India marketplace guidance is more restrictive than the general Connect feature set: it states that separate charges and transfers and standalone transfers are not currently supported for Indian platforms; manual payouts to connected accounts are supported only for limited use cases and require contacting Support. [Stripe India marketplace support](https://support.stripe.com/questions/stripe-india-support-for-marketplaces)
- Stripe Connect is a product for platforms and marketplaces with multiple parties, but India Connect onboarding has country-specific limitations and eligibility. Confirm the exact account and use case with Stripe rather than assuming general Connect docs apply. [Stripe Connect overview](https://stripe.com/in/connect), [India Connect onboarding](https://support.stripe.com/questions/onboarding-requirements-for-stripe-connect-in-india)
- Stripe documents “separate charges and transfers” as a marketplace funds flow; that is a charge associated with a business transaction, not a generic facility for sending personal money. [Separate charges and transfers](https://docs.stripe.com/connect/separate-charges-and-transfers)
- Stripe documentation allows reversal of some Connect transfers, with balance and charge constraints; refund/reversal and negative-balance responsibility therefore need explicit design. [Transfer reversals](https://docs.stripe.com/api/transfer_reversals)

### India regulatory considerations

- RBI's PPI Master Directions establish conditions for PPI issuers and payment instruments. Whether the proposed product constitutes a PPI or another regulated payment activity depends on the actual funds flow and legal structure; obtain Indian payments counsel and a regulated partner's written position before holding or transmitting user funds. [RBI PPI Master Directions](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12156)
- Real digital lending must be built with a regulated entity and meet the current RBI Digital Lending Directions. This Stripe plan does not authorize or implement lending. [RBI Digital Lending Directions, 2025](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12848&Mode=0)

**Research interpretation:** the public Stripe materials do not show that this app's P2P wallet model is eligible. Only Stripe can decide whether a precisely described marketplace use case is approvable for this account. This document is an engineering plan, not legal advice or a claim of Stripe approval.

## Required decisions and approval gate

Before coding Connect or activating live money movement:

1. Write the business flow in plain language: who pays, who legally sells/provides the service, who owns each balance, who receives funds, whether funds are held, and how refunds/disputes work.
2. Choose one scope: own-merchant checkout, marketplace seller payouts, or P2P wallet. Do not combine them under one generic `send` action.
3. Ask Stripe Support/account team for written confirmation covering: India platform account eligibility; this exact business and product; Connect availability; each connected-account country and entity type; account onboarding configuration; INR charge/settlement currencies; permitted payment method; transfer and payout capabilities; fund-flow restrictions; reserves, refunds, disputes and negative balances.
4. Ask Indian payments counsel/regulated partner whether the funds flow requires a PPI, PA, UPI/TPAP, escrow, or other authorization/partnership. Do not infer an authorization from Stripe account activation.
5. Keep `STRIPE_MODE=test`, `STRIPE_LIVE_ENABLED=false`, and the approval flag false until the written Stripe decision and legal/partner review are archived and reviewed by the responsible operator.

If Stripe declines the marketplace or wallet model, stop the Connect branch and evaluate an RBI-authorized Indian provider/partner. Do not disguise a P2P transfer as a merchant purchase or use Stripe top-ups as a workaround.

## Implementation plan if Stripe approves marketplace payments

This branch is only for genuine purchases from onboarded sellers. It does not enable consumer P2P sends or a withdrawable wallet.

### Phase 0 — freeze current boundary

- Keep send/withdraw/cash-out UI disabled and remove any success wording for unavailable actions.
- Label the current balance and top-up as test-only/non-transferable; do not imply cash-like stored value.
- Keep Stripe credentials server-side and live gates off.

### Phase 1 — define the canonical model

Add provider-neutral records (migrations required):

- `merchant_accounts`: internal seller ID, Stripe connected account ID, country, onboarding/capability state, required-action state, timestamps. Never accept a connected account ID from an untrusted client as authorization.
- `payment_orders`: authenticated buyer, seller, business reference, amount/currency, status, Stripe Checkout/PaymentIntent ID, idempotency key and lifecycle timestamps.
- `transfers`: source payment/order, destination merchant, amount, transfer group, Stripe transfer ID, transfer/reversal state and failure reason.
- `payment_events`: unique provider event ID, event type, payload hash/limited safe metadata, received/processed timestamps; avoid retaining unnecessary sensitive payload.
- `ledger_entries`: immutable double-entry accounting for internal reporting/reconciliation. It must not represent independently redeemable user balances unless a separately approved wallet product exists.
- `refunds` and `disputes`: provider IDs, amount, current state and linked original payment/transfer.

Use integer minor units and explicit currency. Store append-only state transitions/audit records. Add unique constraints for provider event IDs, order idempotency keys, provider object IDs and one-time transfer creation per business event.

### Phase 2 — seller onboarding and capabilities

- Backend creates Connect onboarding links/sessions only for an authenticated seller using Stripe-approved onboarding mode.
- Persist the connected account ID on the seller record; never expose secret key or let buyer choose arbitrary destination accounts.
- Consume verified account/capability updates and prevent payments or transfers until Stripe confirms the required capabilities.
- Provide seller status UX for `pending`, `restricted`, `ready`, and `disabled`; do not collect identity documents in app unless Stripe and legal review require a separate compliant design.

### Phase 3 — create and settle a real marketplace order

Proposed REST contracts (only after approval):

- `POST /api/v1/merchant-accounts/onboarding-sessions` — seller-authenticated; returns an expiring Stripe-hosted onboarding URL.
- `GET /api/v1/merchant-accounts/me` — seller-owned capability/onboarding summary.
- `POST /api/v1/merchant-orders` — buyer-authenticated; accepts seller ID, catalog/order reference and idempotency key; server loads price and destination mapping.
- `GET /api/v1/merchant-orders/{order_id}` — buyer or seller with explicit ownership; safe canonical state only.
- `GET /api/v1/activity` — caller-owned normalized activity with pagination/cursors.
- `POST /api/v1/merchant-orders/{order_id}/refunds` — authorized support/admin or contractually permitted seller role; idempotent and audited.

Flow:

1. Backend checks authenticated buyer, active seller, approved capability, server-calculated amount/currency, order ownership and idempotency.
2. Backend creates Checkout/PaymentIntent with the approved Connect charge model and stable metadata mapping to the internal order. Do not trust client success redirects.
3. Stripe signed webhooks are verified from raw request bytes, deduplicated, then update canonical payment state transactionally.
4. Only after the configured marketplace business event and policy conditions are satisfied does the backend create the approved related transfer. Do not create a transfer from a wallet top-up.
5. User history updates from server records/webhooks; client polls or receives a notification but never determines settlement.
6. Refund, dispute, reversal, failed transfer and payout states are persisted and reconciled. A successful card charge is not necessarily a successful seller bank payout.

### Phase 4 — operations and controls

- Build scheduled reconciliation against Stripe balance transactions, charges, transfers, reversals, payouts and refunds; surface unmatched records for operations.
- Set transfer/payout limits, velocity checks, seller eligibility, sanctions/fraud review and manual hold/release controls consistent with Stripe requirements.
- Define support process for failed/returned payouts, disputes, chargebacks, seller negative balances, refunds after transfer, account deactivation and webhook outages.
- Redact PII/payment tokens in logs; add operator audit trail and role-based access for financial support actions.
- Review privacy retention, tax reporting, grievance handling and financial statements with Stripe and counsel.

### Phase 5 — sandbox verification and staged release

Run deterministic tests using Stripe test mode and test connected accounts before production review:

- onboarding incomplete, restricted, enabled and disabled account states;
- successful/declined/cancelled/pending payment; webhook duplicates, reordering, signature failure and retry;
- duplicate order submission; duplicate transfer prevention; insufficient platform/connected balance; reversal/refund and dispute cases;
- two-user authorization matrix for buyer, seller and support; object ID guessing must reveal no other party's data;
- payout pending/paid/failed/returned and reconciliation mismatch;
- mobile return/deep-link interruption and app restart;
- history pagination and canonical state under webhook delay.

Production acceptance requires written Stripe approval, legal/partner sign-off, production dashboard capabilities, successful sandbox evidence, documented reconciliation and incident runbooks, and staged limits. No live money test should be run with real users as a substitute for these gates.

## If the requested feature is P2P send or general wallet cash-out

Do not implement it via Stripe. Re-scope it to an authorized Indian PPI/bank/UPI/payment partner that explicitly supports the required user-to-user and cash-out flow. Then create a separate integration plan for that partner including KYC ownership, payer/payee addressing, transaction limits, consent/authentication, fraud controls, disputes, reversals, accounting ledger, reconciliation, complaints and regulatory reporting. Stripe may remain only for separately approved merchant purchases, not as a wallet funding shim.

## Current blockers

- No written Stripe approval for Connect or this product's payment/wallet/P2P model is recorded in the repository.
- No Stripe Connect account onboarding, connected-account persistence, transfers, payouts, refund/dispute state machine or reconciliation implementation exists.
- Current Stripe use is top-up only; its configured account and live/test behavior were not dynamically verified during this research.
- The intended business model (merchant of record vs third-party marketplace vs P2P) and target payee country are still not established.
- No Indian payment partner or regulated lender contract is established in the repo.

## Source references

- [Stripe India account availability](https://support.stripe.com/questions/stripe-accounts-are-invite-only-in-india)
- [Stripe India payment methods](https://support.stripe.com/questions/supported-payment-methods-currencies-and-businesses-for-stripe-accounts-in-india?locale=en-GB)
- [Stripe restricted-business FAQ](https://support.stripe.com/questions/prohibited-and-restricted-business-list-faqs)
- [Stripe Connect overview](https://stripe.com/in/connect)
- [Stripe Connect onboarding requirements in India](https://support.stripe.com/questions/onboarding-requirements-for-stripe-connect-in-india)
- [Stripe separate charges and transfers](https://docs.stripe.com/connect/separate-charges-and-transfers)
- [Stripe transfer reversals](https://docs.stripe.com/api/transfer_reversals)
- [RBI PPI Master Directions](https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12156)
- [RBI Digital Lending Directions, 2025](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12848&Mode=0)
