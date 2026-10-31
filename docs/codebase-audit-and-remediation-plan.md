# Technical Research Brief: Ubanku and Sahayak App Audit

**Scope:** React Native/Expo client, FastAPI backend, wallet/payment and loan-readiness flows, auth, navigation, and project documentation.  
**Status:** Baseline audit completed 2026-10-31 before demo-wallet implementation. This report preserves the original findings and remediation rationale; current demo-wallet behavior is documented in `app.md` and `financial-app-readiness-plan.md`.

## 1. Executive Summary

The repository contains two overlapping product experiences: a legacy Ubanku wallet/banking demo and the newer Sahayak financial journey app. Their screens and labels do not consistently reflect the same backend capabilities. The Sahayak wallet balance is computed from verified Stripe test top-up credits, but sends are stored separately as `SIMULATED` records and cannot spend that balance; withdrawals are unavailable. Loan screens calculate synthetic offers and track readiness only; they do not originate or service loans. The legacy Ubanku home still displays a hard-coded ₹150,000 goal/balance-like figure and routes users into wallet actions, which is a strong source of confusion.

Recommendation: first make the product boundary consistent in navigation and UI, then harden authentication and wallet accounting contracts, then decide whether the target is a non-monetary demo or a real payment product. Real send/withdraw/loan servicing requires a supported payment or lender partner and a separate ledger/state model; it cannot be safely completed by wiring the current Stripe top-up balance into those actions.

## 2. Problem Statement and Objectives

The audit answers:

- What is active in the app and which frontend screens call backend APIs?
- Where are wallet funds actually created, displayed, or spent?
- Do “send,” “withdraw,” and loan actions represent real transactions or demo state?
- Which inconsistencies or security/integration gaps should be resolved first?

The repository is a demo. Findings below distinguish observed implementation from the product direction that still needs a decision. `.env` contents were not inspected.

## 3. Current Architecture and Implementation Reality

### App composition

- `App.tsx` and `src/navigation/RootNavigator.tsx` host the signed-in navigation. `TabNavigator` maps the first tab to `SahayakJourney`, the second to chat, the third to `HomeWallet`, and retains `Home` under a separate “Ubanku” tab ([TabNavigator.tsx](../src/navigation/TabNavigator.tsx#L41)).
- The legacy Ubanku home has a hard-coded `₹150000` and 45% progress and exposes deposit, withdraw, and send navigation ([Home.tsx](../src/screens/Home.tsx#L87)). That figure is unrelated to the server wallet endpoint.
- Active email login and registration use FastAPI through `AuthContext`; old phone/PIN screens and mock user storage remain in the source tree but are not in the active `AuthNavigator` ([AuthNavigator.tsx](../src/navigation/AuthNavigator.tsx#L21), [AuthContext.tsx](../src/contexts/AuthContext.tsx#L116), [MockDataService.ts](../src/services/MockDataService.ts#L1)).

### Main data paths

```text
Wallet tab -> getServerWalletBalance(token)
  -> GET /api/v1/wallet/balance
  -> sum(wallet_ledger_entries.amount_paise for current user)

Add money -> createStripeWalletTopup(token, amount)
  -> POST /api/v1/wallet/payment-orders
  -> Stripe Checkout -> signed webhook -> payment_orders status
  -> idempotent wallet_ledger_entries credit -> balance refresh

Send demo -> createDemoTransfer(token, recipient, amount)
  -> POST /api/v1/demo/transfers
  -> demo_transfers row with SIMULATED status (no wallet debit)

Loan journey -> /api/journeys + /api/financial calculate + consent/doc preflight
  -> synthetic offer/readiness state only; no lender application or loan account
```

Evidence: client API functions live in [sahayakApi.ts](../src/services/sahayakApi.ts#L180); balance aggregation is in [payment_orders.py](../backend/app/api/payment_orders.py#L206); successful top-up ledger credit is webhook-driven in [payment_service.py](../backend/app/services/payment_service.py#L471); send is explicitly documented and implemented as a separate simulated record in [SendPage.tsx](../src/screens/Wallet/SendPage.tsx#L19) and [payment_orders.py](../backend/app/api/payment_orders.py#L44).

### Verified findings

1. **The active Sahayak send flow does accept any positive amount even if the wallet shows ₹0.** This is by design in the current code: the form validates only recipient and positive amount, and the API inserts a demo row without checking or debiting the wallet ([SendPage.tsx](../src/screens/Wallet/SendPage.tsx#L19), [payment_orders.py](../backend/app/api/payment_orders.py#L51)). It does not transfer money. The UI has explicit simulation warnings, but the “Send” affordance and legacy screens make that distinction easy to miss.
2. **Wallet balance is credits-only, not available balance.** `GET /wallet/balance` sums successful top-up credit rows and the ledger model only supports credit entries; there are no debit/reservation/transfer entries or available-balance constraints ([payment_orders.py](../backend/app/api/payment_orders.py#L206), [db_models.py](../backend/app/models/db_models.py#L149)).
3. **Top-ups are Stripe Checkout orders and ledger credits, currently described as test-only.** The deposit pages create the order and refresh status; the webhook credits only when provider status, amount, and currency match ([DepositConfirmPage.tsx](../src/screens/Wallet/DepositConfirmPage.tsx#L16), [payment_service.py](../backend/app/services/payment_service.py#L493)). This is not a general-purpose transferable wallet.
4. **Withdrawals are unavailable.** The screen says payouts/bank withdrawal are not configured ([WithdrawDetailsPage.tsx](../src/screens/Wallet/WithdrawDetailsPage.tsx#L1)); there is no payout endpoint in `payment_orders.py`.
5. **Loan actions are readiness assistance, not lending.** Journeys can be created, revised, moved through readiness stages, and calculated against synthetic offers. No disbursement or loan repayment endpoint exists. Stripe order creation rejects non-wallet top-up purposes ([payment_orders.py](../backend/app/api/payment_orders.py#L129)); the existing journey routes and owner checks are in [journeys.py](../backend/app/api/journeys.py#L104).
6. **The old Ubanku view does not match this server model.** Its hard-coded ₹150,000 and progress indicator are not connected to wallet state ([Home.tsx](../src/screens/Home.tsx#L87)); its withdraw/send shortcuts imply capabilities that are disabled or simulated.
7. **Payment history is split.** The wallet screen combines provider top-up orders with simulated send rows and labels the difference, but it is not a complete statement or a unified ledger ([WalletTransactionsPage.tsx](../src/screens/Wallet/WalletTransactionsPage.tsx#L69)). The wallet home itself displays only top-up ledger credits ([HomeWallet.tsx](../src/screens/HomeWallet.tsx#L50)).
8. **Session restore can trust cached state during backend unavailability.** If `/api/auth/me` fails, `AuthContext` restores the cached profile/token as authenticated ([AuthContext.tsx](../src/contexts/AuthContext.tsx#L56)). The backend still validates protected API calls, so this can produce a signed-in UI with failing requests and misleading empty/default states.
9. **Journey creation allows unauthenticated records under a shared demo identity.** `POST /api/journeys` uses optional auth and assigns `user_sahayak_demo` when no current user exists; ownership verification explicitly exempts that identity ([journeys.py](../backend/app/api/journeys.py#L25), [journeys.py](../backend/app/api/journeys.py#L104)). This is acceptable only for a deliberately public demo path and needs isolation before journeys are treated as private customer data.
10. **Documentation already records the intended boundary.** [app.md](../app.md#L1) and [stripe-money-movement-research-plan.md](./stripe-money-movement-research-plan.md#L1) say this is a demo, distinguish simulated sends, and describe provider/legal approval gates. The UI/navigation remains inconsistent with those boundaries.

## 4. Approaches and Trade-offs

| Approach | Outcome | Complexity | Risk/fit |
| --- | --- | --- | --- |
| **A. Clearly bounded demo (recommended immediate choice)** | Make all app areas describe simulated journeys/test top-ups consistently; disable real-sounding send, pay, withdrawal, cashback, and loan-servicing claims. | Low to medium | Lowest integration risk; does not provide real money movement. |
| **B. Approved merchant purchase flow** | Keep Stripe for a genuine merchant product checkout with fulfillment/refund handling; do not call it a wallet top-up or allow P2P/cash-out. | Medium to high | Depends on Stripe approval and a real merchant/service model. Not a shortcut for P2P. |
| **C. Real wallet, transfer, and lending product** | Integrate an eligible regulated payment partner and regulated lender; implement provider-neutral double-entry accounting, transaction state machines, reconciliation, disputes, KYC/limits, and role controls. | High | Correct direction for actual banking-like behavior; requires external commercial, regulatory, operational, and security readiness. |

## 5. Recommended Remediation Plan

### Phase 0 — Establish one demo truth across the UI

1. Pick the canonical app identity and decide whether the Ubanku tab remains visible. If it stays, label it as a legacy showcase and remove balance-like values that look spendable.
2. Rename simulated send entry points and button copy; avoid “Pay,” “Send,” or success states that suggest movement. Prefer a distinct “Try a simulated send” demo action.
3. Make unavailable actions visibly disabled or route directly to an unavailable explanation. Remove misleading legacy success strings from `LanguageContext` for deposit/withdraw/send.
4. Add loading, error, and stale-data states to wallet balance. Do not convert API failure into a displayed ₹0 balance, because “could not load” and “zero balance” are different states (`HomeWallet.tsx` currently clears balance to zero on request failure).
5. Align home tiles, wallet balance, transactions, and loan labels with the demo/readiness model. Keep synthetic cashback/referral cards explicitly marked or remove them from active surfaces.

### Phase 1 — Tighten contracts and account/session behavior

1. Make protected app journeys require auth; remove the shared `user_sahayak_demo` exception from any customer-facing route, or isolate it behind an explicit public-demo namespace with no private documents/consent.
2. Treat `/api/auth/me` failure as unauthenticated unless it is a transient offline mode that is explicitly surfaced; do not set `isAuthenticated` from cached identity alone.
3. Centralize transaction purpose/status models and client labels so the UI cannot call a `SIMULATED` event “sent” or show a test credit as withdrawable funds.
4. Ensure an idempotency key is stable per user action across retries and app restarts. The client passes a screen-route `operationId` as the API idempotency key, but it is created with `Date.now()` on the prior deposit screen and is not persisted independently ([DepositPage.tsx](../src/screens/Wallet/DepositPage.tsx#L36), [DepositConfirmPage.tsx](../src/screens/Wallet/DepositConfirmPage.tsx#L37)).
5. Make all money-facing API failures visible and distinguish provider pending, success, failed, expired, and reconciliation-required states.

### Phase 2 — Decide and implement the correct ledger model

If remaining a demo, use a database-only simulated balance and never accept real card funds for it; keep sends simulation-only and do not enforce them against top-ups as if they were spendable.

If pursuing real money movement, replace the credit-sum representation with an append-only double-entry ledger in integer minor units. Model pending authorization/reservation, settlement, debit, reversal, refund, and available balance. Perform balance checks and debit/reservation atomically on the server, use unique idempotency constraints, and prohibit client-side balance authority. Do not enable a transfer until a provider supports this exact user-to-user flow and the account/product is approved.

### Phase 3 — Test and release gates (after implementation is requested)

Add server tests for zero/insufficient balance, exact-balance send, concurrent sends, duplicate requests, webhook duplication/reordering, amount/currency mismatch, ownership isolation, and stale-session behavior. Add client flow coverage for loading/error/zero states, checkout return/restart, and honest simulated-versus-provider labels. Verify test mode end-to-end before any deployment; live payment movement needs provider approval, legal/partner review, reconciliation, support and incident procedures.

## 6. Scope Boundaries and References

Repository guidance says Stripe top-ups are test/demo only, Stripe Connect/P2P support is not established, and real loan servicing needs an authorized lender. See [Stripe money movement research plan](./stripe-money-movement-research-plan.md) and [financial app readiness plan](./financial-app-readiness-plan.md). This review is an engineering code audit, not confirmation of provider or regulatory eligibility.

Files and routes were inventoried across the repository, then the active app composition and connected auth, wallet, journey, payment, and persistence paths were traced in detail. This is a focused cross-cutting audit, not a line-by-line review of every asset and legacy screen. No automated tests were run as this request asked for research and planning.
