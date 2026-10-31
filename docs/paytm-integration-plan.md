# Paytm Payment Gateway Integration Plan

**Status:** Historical research only. The Paytm routes, service, environment settings and dependency were removed from the active app. The selected active demo path is Stripe test Checkout; see [the Stripe integration status](stripe-migration-plan.md).  
**Reviewed:** 2026-10-31  
**Target:** Hackathon staging demo for one-time INR wallet top-up, with a clear separation between simulated wallet actions and Paytm-verified payment.

> The remainder of this document is a historical snapshot from before the Stripe switch. Its implementation instructions and file paths are stale; do not follow them for the current app. For current scope and limits, use the Stripe status and [financial readiness plan](financial-app-readiness-plan.md).

## 1. Recommendation

Paytm is a reasonable provider for an India-first demo if the hackathon expects UPI/Paytm checkout. Use Paytm staging credentials and implement one end-to-end collection flow first. Do not describe the current wallet as connected: its balance and transactions are still stored in device `AsyncStorage` ([walletDemoStore.ts](../src/services/walletDemoStore.ts#L1-L20)).

The app is **not ready for a provider-only switch**. The current backend payment order, model, response schemas, status reconciliation, and webhook handling are Stripe-specific ([payment_orders.py](../backend/app/api/payment_orders.py#L26-L152), [payment_service.py](../backend/app/services/payment_service.py#L102-L243), [db_models.py](../backend/app/models/db_models.py#L96-L144)). The mobile app has no payment provider SDK dependency and does not call the payment-order routes. The account also has no Paytm configuration in the checked-in example environment.

Recommended MVP: Paytm staging **wallet top-up collection** with native checkout on the target phone platform, or Paytm web checkout if the judges will use the current browser/Expo Web demo. Keep withdrawals and person-to-person transfers labeled simulated; Paytm Payment Gateway collection does not itself implement those wallet operations.

## 2. Research objectives and scope

This plan covers the Paytm Payment Gateway (PG) one-time transaction flow:

- Create a server-owned payment order with a server-computed INR amount.
- Initiate a Paytm transaction and return only the short-lived transaction token and required public checkout values to the app.
- Launch checkout using a platform-appropriate Paytm integration.
- Verify the final transaction state server-to-server before reporting success or crediting a demo ledger.
- Handle duplicate requests, callbacks, pending states, failure, cancellation, reconciliation, and refunds.

It does not treat PG as the solution for outbound withdrawals, wallet-to-wallet transfers, lending disbursement, recurring repayment mandates, or a production stored-value wallet. Those are separate products and approval/integration scopes.

## 3. Current codebase reality

### Existing payment backend

- `POST /api/v1/payment-orders` creates a persistent order, but permits an optional/anonymous caller and labels it with a demo user. Real collection must require an authenticated user ([payment_orders.py](../backend/app/api/payment_orders.py#L47-L72)).
- `create_payment_order` computes INR paise, writes an order and audit row, then calls Stripe directly ([payment_service.py](../backend/app/services/payment_service.py#L102-L243)).
- `PaymentOrderModel` stores Stripe intent/client-secret columns; provider event rows default to Stripe ([db_models.py](../backend/app/models/db_models.py#L96-L132)).
- Webhook signature verification, event transitions, and reconciliation are Stripe-specific ([payment_orders.py](../backend/app/api/payment_orders.py#L107-L152), [payment_service.py](../backend/app/services/payment_service.py#L297-L470)).
- Supabase mirroring currently forwards Stripe-specific fields too ([supabase_service.py](../backend/app/services/supabase_service.py#L34-L67)); update its payload/schema if payment orders continue to be mirrored after provider generalization.
- The Stripe adapter can fabricate test-shaped intent values when keys are absent, so the Paytm adapter must fail closed on missing staging configuration rather than imitate a successful checkout ([stripe_service.py](../backend/app/services/stripe_service.py#L16-L99)).
- There are legacy Stripe endpoints under `/api/financial/create-payment-intent` as well as the persistent order API. The Paytm flow should use the persistent order lifecycle and should not reuse that legacy PaymentIntent response.

### Existing wallet client

- Wallet state starts with a hard-coded demo balance and persists operations locally. Deposit, withdrawal and send confirmation screens call `recordWalletOperation`; no server payment/order call is made ([walletDemoStore.ts](../src/services/walletDemoStore.ts#L1-L20), [DepositConfirmPage.tsx](../src/screens/Wallet/DepositConfirmPage.tsx#L1-L21)).
- The demo cannot safely display a Paytm order as a completed deposit just because the SDK returned a success-like callback. The backend must verify the order and create the ledger credit exactly once.

### Native/web compatibility

- The app is Expo/React Native with Android and iOS projects, but no Paytm SDK dependency is currently declared ([package.json](../package.json#L24-L45)).
- Paytm's official React Native repository documents `startTransaction(orderId, mid, txnToken, amount, callbackUrl, isStaging, ...)`, plus manual native setup and URL-scheme handling. Its README uses legacy `react-native link` steps, so it is a compatibility risk with this app's current Expo/React Native versions. Verify a minimal native build before building the checkout UI around it. [Official Paytm React Native SDK repo](https://github.com/paytm/paytm-allinonesdk-react-native)
- Paytm says its All-in-One SDK supports Android/iOS and hybrid frameworks including React Native, but the SDK is not supported through mobile web. Browser checkout therefore needs a web checkout route instead of assuming the native SDK works in Expo Web. [Paytm All-in-One SDK](https://business.paytm.com/all-in-one-sdk)

## 4. Paytm flow and product fit

For the standard one-time PG flow, the merchant backend initiates the transaction and receives a transaction token; checkout presents the payment methods enabled for the merchant; then the backend verifies the result with Paytm's Transaction Status API before fulfilling the order. Paytm requires server-side verification of order ID and amount and says to treat the status API response as final. [Paytm Custom Checkout flow](https://www.paytmpayments.com/docs/v1/custom-checkout), [Paytm staging test instruments](https://www.paytmpayments.com/docs/test-instruments/testing-integration)

Paytm lists UPI, cards, net banking, Paytm wallet and other options for its checkout products, but which options are actually available depends on merchant configuration. Confirm the staging MID's enabled modes before promising a specific checkout option. [Paytm onboarding and credentials](https://www.paytmpayments.com/docs/get-started-with-paytm-integration-merchant-onboarding/)

Paytm PG is an inbound collection flow. Refunds can be initiated for eligible successful/settled transactions through Paytm's refund facility, but refund initiation/status should be a separate feature and ledger transition. [Paytm refund overview](https://business.paytm.com/docs/pos-other-supported-flows/)

The current app's withdrawal/send buttons are not covered by a PG integration. Paytm Payouts is a distinct merchant product with its own disbursal workflow and eligibility; do not route these actions through the top-up flow. [Paytm Payouts overview](https://www.paytmpayments.com/docs/paytm-payouts/introduction-internal)

## 5. Integration architecture

```text
Wallet screen
  -> authenticated POST /api/v1/payment-orders (purpose=wallet_topup)
  -> Sahayak API persists CREATED order and calls Paytm Initiate Transaction
  -> API returns order_id, amount, MID/public config, txnToken, expiry
  -> Web checkout OR native Paytm All-in-One SDK
  -> app sends order_id to backend verify endpoint / polls order status
  -> backend calls Paytm Transaction Status API and validates MID/order/amount/currency
  -> backend records terminal status + audit/event exactly once
  -> on verified success only: create one wallet ledger credit
  -> client refreshes canonical server wallet balance and transaction history
```

### Provider boundary

Introduce a small provider interface around the existing order lifecycle rather than duplicating all business rules in a second Paytm-specific order system:

- `initiate(order) -> provider checkout data`
- `verify(order) -> canonical provider status`
- `parse/verify notification(raw request) -> provider event` (if using merchant webhooks)
- `refund(order, amount) -> refund request/status` (later milestone)
- optional `reconcile(order)` for stale `PENDING`/`PROCESSING` orders

Keep amounts, ownership, status transitions, audit trail and ledger posting provider-neutral. Implement the Paytm adapter separately. Keep Stripe tests/adapter working during the hackathon unless the team explicitly decides to remove Stripe later.

### Payment order/data changes

Use a migration, not `create_all` alone, for an existing database. Add general provider fields such as `provider`, `provider_order_id`, `provider_transaction_id`, and a provider status/reference. Return a typed checkout object that can represent Stripe client-secret or Paytm `txnToken` without exposing merchant secrets. Retain legacy Stripe columns during the compatibility period, then migrate consumers before dropping them. Change provider-event uniqueness to `(provider, provider_event_id)`; where Paytm sends no stable event ID, make order-state transitions and ledger posting idempotent on the stored Paytm order/transaction identifiers.

Add a `wallet_ledger_entries` table (or equivalent append-only ledger) with user, order, direction, INR paise, status, timestamps, and a unique source payment-order constraint. Wallet balance should be computed/materialized from confirmed ledger entries, never from the client. Do not double-credit on repeat verify calls or duplicate callbacks.

### API proposal

- `POST /api/v1/payment-orders`: require bearer auth and idempotency key; validate top-up bounds server-side; create the resource and initiate Paytm. Return `201` with provider-neutral order fields and a Paytm checkout payload. Use `401` for missing auth, `422` for invalid amount/currency, and `409` for an idempotency key reused with different order data.
- `GET /api/v1/payment-orders/{order_id}`: owner-only canonical order state; return `404` for an unknown or inaccessible order.
- `POST /api/v1/payment-orders/{order_id}/verification`: owner-only non-CRUD status check; server calls Paytm, validates expected merchant/order/amount/currency and updates canonical state. Return `200` with the order state; provider timeouts leave the order pending/reconcilable and must not be reported as failure or success.
- `POST /api/v1/webhooks/paytm`: optional public notification endpoint with Paytm checksum verification, provider-event dedupe, and server-side status recheck. Return a stable acknowledgement for duplicate valid notifications; reject invalid signatures. Never accept an unsigned client callback as final.
- `GET /api/v1/wallet`: owner-only balance and ledger history.

Example create response (field names are proposed, not implemented):

```json
{
  "order_id": "po_...",
  "provider": "paytm",
  "purpose": "wallet_topup",
  "amount_paise": 10000,
  "currency": "INR",
  "status": "REQUIRES_ACTION",
  "checkout": {
    "mid": "staging MID",
    "txn_token": "short-lived token",
    "environment": "staging",
    "callback_url": "provider/app callback URL"
  }
}
```

Keep `txnToken` short-lived and only return it to the authenticated owner. The Paytm merchant key must remain server-side. Do not trust amount, transaction status, MID or order ID values supplied back from the app; compare provider responses against the stored order.

## 6. Platform decision

There are two checkout paths; select based on the actual hackathon demo target:

| Demo target | Recommended checkout | Engineering notes |
| --- | --- | --- |
| Android/iOS installed app | Paytm All-in-One SDK via its React Native bridge, after a native compatibility spike | Needs custom native build/dev client, Android dependency configuration, iOS URL schemes/return handling, and staging UPI test app for intent tests. |
| Browser/Expo Web | Paytm-supported web checkout (JS Checkout/Custom Checkout) | Implement a web-specific checkout handoff. The native All-in-One SDK does not support mobile web. |
| Both | Separate web and native checkout adapters sharing the same backend order/verify/ledger API | Do not fork order/status business logic per platform. |

Paytm's official RN plugin instructions include manual native setup and app-invoke URL handling. A zero-screen compatibility spike should prove Android and iOS builds, return-to-app, cancellation, and a staging transaction on the current RN/Expo versions before committing to the plugin. If that spike fails or is too costly for the hackathon, prefer supported web checkout for the browser demo rather than writing an unreviewed native bridge under time pressure.

## 7. Phased implementation plan

### Phase 0 — Confirm merchant and demo constraints

1. Create/confirm Paytm for Business merchant access and retrieve **staging** MID and merchant key from its dashboard. Staging MID is available in the dashboard; production credentials are provided after account activation. Keep the merchant key only in backend environment/secrets. [Paytm onboarding](https://www.paytmpayments.com/docs/get-started-with-paytm-integration-merchant-onboarding/)
2. Confirm account has PG staging access, the allowed payment modes, and whether refund/status notifications are enabled.
3. Decide the hackathon demo target: browser, Android device/emulator, iOS device/simulator, or both.
4. Freeze MVP purpose as one-time `wallet_topup` using test money. Leave withdrawal/send, real EMI collection, subscriptions, payouts and live transactions out of scope.

**Gate:** real provider calls remain disabled until staging credentials and target platform are configured. The code path may be implemented behind a disabled-by-default flag.

### Phase 1 — Provider and order foundation

1. Configure `PAYTM_ENVIRONMENT=staging`; set MID, merchant key, website name and optional callback URL in ignored backend `.env`/deployment secret store. Do not place secrets in Expo `EXPO_PUBLIC_*` variables.
2. Add Paytm's server-side Python checksum/PG library or directly use its official REST contract behind a small adapter. Pin and review the dependency; use the official checksum utility and test its verification behavior. [Paytm Python checksum library](https://github.com/paytm/Paytm_Python_Checksum), [Paytm server SDKs](https://www.paytmpayments.com/docs/server-sdk/)
3. Generalize provider metadata in persisted payment orders with a forward migration. Preserve current Stripe columns and behavior until regression tests pass.
4. Make payment order creation owner-authenticated. Validate top-up amount, currency INR, unique merchant `ORDER_ID`, idempotency and metadata server-side.
5. Add backend Paytm transaction initiation and return only fields required by the selected checkout integration.

**Gate:** backend tests prove amount and order are server-owned, credentials never enter responses/logs, and duplicate initiation with one idempotency key returns the same order.

### Phase 2 — Checkout and authoritative verification

1. Implement the selected platform checkout (native bridge or web checkout) using only backend-issued `order_id`, `txnToken`, configured staging MID and amount.
2. Treat SDK/browser result as a user-facing hint. Add owner-authenticated verify/poll route that queries Paytm Transaction Status API from the backend.
3. Validate Paytm response checksum and match MID, merchant order ID, exact expected paise/INR amount and final status against the database order. Persist transaction ID, final status, provider event/audit details.
4. For `PENDING`/unknown/timeouts, show “checking payment” and poll/reconcile; never mark successful from timeout or navigation return.
5. Add a signed notification route when Paytm requires/configures webhooks. Paytm states webhook URLs must be publicly accessible and currently allow port 443; use an HTTPS staging tunnel/deployed test endpoint if testing this path. Keep the status API as the authoritative server confirmation. [Paytm callback/webhook requirements](https://www.paytmpayments.com/docs/callback-and-webhook/)

**Gate:** failed, cancelled, duplicate, tampered and pending events cannot produce a successful ledger credit.

### Phase 3 — Ledger and app UX

1. Add server-owned wallet balance/history APIs backed by the append-only ledger.
2. Replace local balance mutations for the Paytm top-up route only. On verified success, insert exactly one credit tied to the payment order; on other statuses, do not post a credit.
3. Keep local demo wallet functionality available under an explicit simulation label, or remove it from the Paytm test path so the user does not see two competing balances.
4. Display order states (`CREATED`, `REQUIRES_ACTION`, `PROCESSING`, `SUCCEEDED`, `FAILED`, `CANCELED`, `EXPIRED`, `RECONCILIATION_REQUIRED`) and transaction reference; identify all staging transactions as test transactions.
5. Add refund initiation/status only if the hackathon requires it and Paytm enables the feature. Refunds require their own pending/succeeded/failed state transitions and ledger debit/reversal treatment; do not mutate the original credit silently.

### Phase 4 — Staging end-to-end and demo readiness

1. Unit test checksum generation/verification and the provider adapter with mocked HTTP responses.
2. API tests: auth ownership, bounds, idempotency, state transitions, duplicate notifications, amount/MID/order mismatches, checksum errors, and concurrent verify requests.
3. Run Paytm staging tests for success, failure, cancellation, pending/timeout, retry and app interruption. Paytm staging test instruments include selectable success/failure for card/net banking and a test UPI app for Android intent/collect paths. [Paytm test instruments](https://www.paytmpayments.com/docs/test-instruments/testing-integration)
4. Run a Maestro flow against a built native app if native checkout was selected; run a browser E2E flow for web checkout if web was selected.
5. Confirm Paytm dashboard test data and local order/ledger rows agree. Re-run existing backend tests to confirm Stripe behavior did not regress.

**Demo acceptance:** user initiates a test top-up, completes Paytm staging checkout, sees final status only after backend verification, and sees exactly one server ledger credit. A failure/cancel/pending scenario never credits funds.

### Phase 5 — Connect verified payment context to Sahayak AI

**Current baseline:** `/api/chat` can associate a request with an owned loan journey, but the handler explicitly excludes journey values, OCR fields and payment data from model context ([chat.py](../backend/app/api/chat.py#L87-L118)). Its request schema has no payment reference today ([schemas.py](../backend/app/models/schemas.py#L256-L268)), and the mobile client always sends `allow_external_processing: false` ([sahayakApi.ts](../src/services/sahayakApi.ts#L64-L67)). Preserve those protections when adding payment context.

1. Add an explicit “Ask Sahayak about this payment” entry from a payment/order detail view. Extend chat input with optional `payment_order_id` and `include_payment_context=false`. Send only the order reference and opt-in flag; never accept a status, amount, MID, provider callback, or transaction payload from the client as context.
2. If payment context is requested, require an authenticated caller, resolve the order on the backend, verify ownership, and build a short-lived `PaymentContext` projection from the local canonical order and ledger. Return `404` for unknown or other-user orders. Do not put payment records in the shared RAG knowledge base or conversation store.
3. Include only facts needed to answer the request: provider label, INR amount, canonical status, whether the wallet ledger credit exists, and last status update. Do not include the Paytm merchant key, `txnToken`, checksum, callback body, raw provider event, full card/account/UPI data, or unnecessary user identifiers.
4. Provide deterministic, server-side responses for common status questions even while external AI remains disabled. Example rules: `SUCCEEDED` only if backend verification succeeded **and** the unique ledger credit exists; pending states say “still confirming”; failed/canceled/expired say no credit was posted; `RECONCILIATION_REQUIRED` directs the user to human support without guessing.
5. If a generative provider is later enabled, require both the existing per-request external-processing permission and a separate, purpose-specific consent for sending payment context to that provider. Add a user-scoped immutable consent record for `ai_payment_context_processing`; do not attach account-level payment consent to a loan journey (`ConsentAuditModel.journey_id` is currently required). Keep the feature flag off by default; document provider retention/processing before enabling it. Pass the minimal structured projection separately from user text and RAG material.
6. Return a typed `payment_summary` from the API as the source of truth and render it separately from the AI prose. Do not let generated text change an order, initiate a retry/refund, or post a ledger entry. Link to verified actions/screens instead.
7. Extend financial-number validation so an AI answer may repeat only exact values from the verified payment projection, without weakening the existing citation checks for other financial claims. Sanitize the projection and conversation turns before any external provider call.

**AI-context acceptance checks:** cross-user order references return no payment facts; external AI receives nothing unless both consents/flags permit it; logs and traces contain no tokens or raw callbacks; pending/failure cannot be described as paid; a success answer agrees with the independent order/ledger response; AI cannot trigger payment or balance mutations.

## Implementation status (2026-10-31)

- Paytm is **not implemented in the active codebase**. There are no Paytm checkout, transaction status, or webhook routes/services, and no Paytm credentials are configured.
- The app has an isolated simulated demo wallet for funding and QR transfers. It does not call a payment provider and has no cash value.
- Stripe test Checkout order/webhook plumbing exists as a separate optional test path; its test credits are not the demo wallet balance. See the [Stripe integration status](stripe-migration-plan.md).
- A real Paytm staging integration still requires merchant credentials, selection of web vs native checkout, server verification, and a provider-neutral order/ledger flow. Do not use the historical implementation steps above as evidence that a Paytm integration is present.

## 8. Explicit non-goals for the hackathon MVP

- Paytm production payments, real money, settlements or public release.
- Withdrawal, P2P send, bank transfer, loan disbursal, or payout flows; those require a separate Paytm product and approvals.
- Real EMI repayment: the current loan flow is synthetic and has no lender account or repayment schedule.
- Subscriptions/UPI Autopay, stored cards, Paytm Postpaid, offers/EMI subvention, partial refunds, disputes and reconciliation dashboard unless the merchant account and event scope are confirmed.
- Connecting private transaction data to external AI without separate purpose-specific consent and a data-minimization review.
- Replacing email/password app authentication with Paytm login. Paytm checkout is a payment provider, not the app identity system.

## 9. Main risks and mitigations

| Risk | Mitigation |
| --- | --- |
| RN bridge does not build with the current Expo/RN setup | Do Phase 0 native spike first; have web checkout as a distinct fallback path. |
| Merchant mode not enabled for the desired pay option | Confirm staging MID capabilities in dashboard before UI promises UPI/card/wallet. |
| Client says success while provider says pending/failed | Backend Transaction Status verification is the only authority; ledger posting is server-side. |
| Duplicate callback or verify calls double-credit wallet | Unique provider event ID, idempotency key, unique ledger source order, transaction/row locking. |
| Existing optional-auth demo route creates ownerless payments | Require authenticated owner for actual Paytm orders; restrict anonymous simulation to a separate demo mode. |
| API key leaks into app bundle or logs | Merchant key and checksum signing only on backend; redact tokens and payment PII from logs. |
| User mistakes test credit for real money | Prominent staging/test labels; never describe a staging top-up as cash balance. |
| PG is incorrectly used for send/withdraw | Keep those UI operations simulated until a separate payout/ledger/compliance design is approved. |

## 10. Decision checklist before implementation

- [ ] Staging MID and merchant key are available in Paytm Dashboard and safely stored server-side.
- [ ] Demo platform is selected (browser vs native Android/iOS).
- [ ] Staging payment methods are confirmed for the MID.
- [ ] MVP is one-time test wallet top-up; no real withdrawal/send/payout.
- [ ] Android/iOS SDK compatibility spike passes if native checkout is selected.
- [ ] Backend owner-auth requirement, provider migration and ledger approach are accepted.
- [ ] AI payment context stays off by default and has a separate consent, ownership check, minimized projection and deterministic fallback.

## 11. References

- [Paytm custom checkout integration](https://www.paytmpayments.com/docs/v1/custom-checkout)
- [Paytm merchant onboarding, MID and key handling](https://www.paytmpayments.com/docs/get-started-with-paytm-integration-merchant-onboarding/)
- [Paytm All-in-One SDK and platform notes](https://business.paytm.com/all-in-one-sdk)
- [Official Paytm React Native SDK repository](https://github.com/paytm/paytm-allinonesdk-react-native)
- [Paytm server-side Python checksum library](https://github.com/paytm/Paytm_Python_Checksum)
- [Paytm server SDK documentation](https://www.paytmpayments.com/docs/server-sdk/)
- [Paytm Transaction Status and callback/webhook guidance](https://www.paytmpayments.com/docs/callback-and-webhook/)
- [Paytm staging test instruments](https://www.paytmpayments.com/docs/test-instruments/testing-integration)
- [Paytm refunds](https://business.paytm.com/docs/pos-other-supported-flows/)
- [Paytm Payouts overview](https://www.paytmpayments.com/docs/paytm-payouts/introduction-internal)
