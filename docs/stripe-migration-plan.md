# Stripe payment integration status and production boundary

**Status:** Stripe Checkout, webhook, ledger and authenticated order-history plumbing exist for developer testing; a provider round trip has not been verified. Live financial-service use is fail-closed in settings.  
**Scope:** Stripe is a possible card-payment provider only after it confirms in writing that this exact product use is allowed. It does not provide lending, wallet/PPI authorization, UPI support for India accounts, or a general P2P/merchant collection ledger. For the researched Connect-versus-P2P decision and conditional implementation phases, see [Stripe money-movement research and implementation plan](stripe-money-movement-research-plan.md).

**Do not set `STRIPE_MODE=live` for this application based only on having keys.** The backend additionally requires `STRIPE_FINANCIAL_SERVICES_APPROVED=true`, which is an operator attestation that explicit written provider approval was obtained. This flag does not itself establish regulatory authorization. If approval is unavailable, use Stripe only for test-mode demonstrations and select a suitable authorized Indian payment provider/PPI partner for production collection and wallet functions.

For demo loans, simulated EMI schedules and simulated payment history, use the database with an explicit `simulated` marker and never trigger Stripe. Use Stripe only when charging for an actual approved merchant product/service; persist the real order and webhook-verified payment state in the database. Do not accept real card funds to create a reusable wallet balance unless Stripe approves that exact model. Stripe's current India marketplace rules do not support separate charges/transfers for Indian platforms, and manual Connect payouts are limited to certain use cases; see the [India marketplace guidance](https://support.stripe.com/questions/stripe-india-support-for-marketplaces).

## Current state

- Stripe PaymentIntent creation, signed webhook handling, stale-order reconciliation, payment order storage, and idempotent wallet ledger credit already exist in the backend (`backend/app/services/payment_service.py`). An authenticated Stripe Checkout Session route is now used for wallet top-ups.
- Stripe credentials are configured in the ignored root `.env`; backend-specific `backend/.env` values take precedence. Secret values are never copied to the app or documented.
- The legacy/optional Stripe test Checkout path calls the authenticated hosted-checkout order and status endpoints (`src/services/sahayakApi.ts`, `src/screens/Wallet/DepositConfirmPage.tsx`). It is separate from the simulated demo-wallet balance and transfers.
- Generic payment order creation, lookup, and listing require authentication; the wallet history endpoint returns only the caller's orders and does not expose checkout secrets.
- PaymentIntent creation now fails closed on missing credentials or provider network errors; it does not fabricate Stripe-shaped IDs/client secrets. The legacy direct PaymentIntent route is disabled with HTTP 410.
- The wallet balance endpoint sums confirmed ledger credits. It is a top-up credit balance, not a complete spendable wallet: withdrawals, transfers, and debits are outside this migration.
- Server-created wallet orders are the only active payment path. Generic payment-order requests reject loan fees and repayments because there is no lender system of record.

## Target end-to-end flow

1. Authenticated app calls `POST /api/v1/wallet/payment-orders` with amount, `wallet_topup`, INR, and an idempotency key.
2. Backend validates credentials, amount and ownership, persists one order, and creates a Stripe Checkout Session using the server secret key.
3. Backend returns the order ID and hosted checkout URL. No secret API key goes to the client.
4. App opens Stripe-hosted checkout; redirect/cancel callbacks are not treated as final payment success.
5. Stripe sends a signed `checkout.session.completed` event to `POST /api/v1/webhooks/stripe`. Backend verifies the signature, deduplicates events, validates the order/amount/currency, updates canonical status, and credits the wallet ledger once.
6. App polls `GET /api/v1/wallet/payment-orders/{order_id}` and refreshes `GET /api/v1/wallet/balance`. Show success only after the backend confirms `SUCCEEDED` and the ledger credit exists.
7. Sahayak payment context continues to read the canonical order and ledger status, subject to the user's recorded AI-context consent.

## Implementation phases

### 1. Configure test mode

Place these values in ignored `backend/.env`; never put secret values in app variables, source control, screenshots, or chat:

```dotenv
STRIPE_MODE=test
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_LIVE_ENABLED=false
STRIPE_FINANCIAL_SERVICES_APPROVED=false
```

Use Stripe test keys only for the demo. Configure the local webhook forwarder or a reachable HTTPS webhook URL to deliver Checkout Session completion events. Keep live mode disabled. India accounts currently do not support local payment methods such as UPI, netbanking, BNPL or EMI; see [Stripe's India payment-method support](https://support.stripe.com/questions/supported-payment-methods-currencies-and-businesses-for-stripe-accounts-in-india?locale=en-GB). Check Stripe's [restricted-business policy](https://stripe.com/in/legal/restricted-businesses) and get explicit written approval for the exact use case before considering live wallet/financial-service transactions.

### 2. Harden and normalize backend order routes

- Require authentication for create, get, and list payment-order endpoints; enforce owner-only access.
- Use the existing idempotency key and server-side amount validation for wallet top-ups.
- Stripe configuration now fails the request with a clear `503`; fake PaymentIntent and sample publishable-key fallbacks are removed.
- Keep webhook signature verification and event deduplication. Confirm successful intent ID, order metadata, amount, INR currency, and authenticated order ownership before ledger credit.
- Ensure webhook replay and concurrent delivery cannot create more than one ledger credit for an order.
- Retain stale-order reconciliation and make its authorization and operation available to the intended local demo workflow.

### 3. Keep unsupported transfers closed

- Send and withdrawal screens now stop before accepting or recording an operation; the local AsyncStorage wallet simulator is removed.
- Paytm order API routes, service, config and checksum dependency were removed from the active backend. The old Paytm plan is retained as historical research only.
- Stripe is currently used for one test-mode wallet top-up flow. Do not implement P2P transfer, merchant collection on behalf of users, or wallet payouts with a generic PaymentIntent. Stripe Connect and the exact business model require separate eligibility and written approval; otherwise choose a suitable authorized provider.

### 4. Verify and document the demo

- Run backend with a test database and Stripe test keys; verify `/health` and configuration state without printing credentials.
- Test an authenticated top-up through the real app checkout using Stripe test instruments; this has not yet been run in this workspace.
- Verify success, decline, cancellation, duplicate idempotency request, repeated webhook, pending/reconciliation, and user ownership isolation.
- Confirm one successful payment produces exactly one ledger row and the displayed balance refreshes from the API.
- Verify Sahayak reports only backend-confirmed payment data and only when AI payment-context consent is enabled.
- Update `app.md`, README, and Maestro flow with actual verified coverage and remaining limitations.

## Acceptance criteria

- A signed-in user can create and complete a Stripe test-mode wallet top-up from the target app build.
- No payment is marked successful or wallet balance credited from a client callback alone.
- Server verifies Stripe webhook signature and stored order details; repeat events/requests are idempotent.
- Another user cannot view or confirm the order.
- Missing Stripe configuration fails clearly and cannot return a fabricated checkout credential.
- No Paytm checkout code remains in active backend routes/services; there are no local send/withdraw writes.
- Live payments remain disabled until separately configured and explicitly reviewed.

## Known boundaries

This migration covers one-time top-up collection only. It does not implement withdrawals, peer transfers, loan disbursement, recurring EMI mandates, refunds, or a full stored-value wallet ledger. Stripe account eligibility and payment methods depend on the merchant's country and account approval; confirm the account supports the intended INR collection methods before choosing it for an India-first demo.
