If you are building Sahayak AI as a mobile application, think of it as a personal financial journey assistant — one app where users can understand financial services, prepare applications, organize documents, track progress and get help.

I recommend dividing the features into modules. This will help you build the app systematically instead of trying to implement everything at once.

## Implementation status

Reviewed against the current workspace on 2026-10-31. `[x]` means implemented, `[~]` means demo/partial, and `[ ]` means not implemented. A FastAPI backend is now included in `backend/`; its data and offers are synthetic and it is not a production lender/payment service.

**Coverage check: not everything in this feature catalog is implemented.** The connected scope is email/password auth, synthetic loan-readiness journeys and database-backed indicative loan products, server EMI calculation, synthetic document preflight, deterministic chat fallback, separate Stripe test Checkout order plumbing, and an isolated simulated demo wallet for account-to-account QR transfers. Demo wallet funds have no cash value and do not include or spend Stripe test credits. This is a developer demo, not a real money wallet, payment collection service, or lender. Real payments require a configured and approved provider integration. Real loans and repayments require a regulated lender integration; production wallet/UPI needs a provider and regulatory structure that supports it. The remaining sections mark partial or missing work; `[~]` means the product capability is incomplete, even if a backend endpoint exists.

### Current connected Sahayak demo pipeline

Signed-out users use backend email/password auth. Authenticated users enter the Sahayak dashboard. The app calls the local FastAPI backend for session validation, offers/EMI, journey stages, consent, synthetic OCR preflight and chat. Journey data is cached in AsyncStorage per user; the backend SQLite database is the source of truth for server journey state.

- [~] Sahayak dashboard → backend loan journey → synthetic offer and deterministic EMI → audited consent → synthetic document preflight and confirmation → FSM readiness handoff. This is an end-to-end backend demo, not a real lender submission.
- [~] Text chat calls the backend guardrailed endpoint with external processing disabled. It returns deterministic fallback/status guidance; live model processing, voice, and conversation history are not enabled.
- [~] Stripe test Checkout has authenticated test-mode order, hosted checkout, signed webhook verification, one-time database ledger credit and canonical status polling. Separately, the demo wallet supports capped temporary funds, user QR codes, and account-to-account simulated transfers with an atomic debit/credit ledger. The configured local demo account has a seeded ₹1,00,000 simulated balance, 100 demo wallet history entries, and three sample multi-platform loan rows; all loan notes and wallet events are explicitly marked as simulated. Demo wallet funds are not Stripe credits, cash, or withdrawable. Loan catalogue products and rate history are database-backed; a real provider or lender feed is not configured. See the [Stripe migration plan](docs/stripe-migration-plan.md) and [Stripe money-movement research and implementation plan](docs/stripe-money-movement-research-plan.md).
- [~] Authenticated demo payment-behaviour endpoint and deterministic score-question response — reads only simulated repayment rows owned by the signed-in user; excludes Stripe wallet top-ups. It is not a CIBIL/bureau score or credit decision. With no demo repayments or bureau integration, it returns insufficient data. See the [credit score boundary](docs/financial-app-readiness-plan.md#credit-score-demonstration).
- [~] Loan-readiness history is available from the authenticated backend journey list. Each item is a readiness/handoff record only; it does not mean a loan was approved, disbursed, or is being repaid. There is no actual loan account, lender application status, repayment schedule, or repayment history.
- [~] Loans tab tracks authenticated demo/user-entered loan records with outstanding balances, EMI amounts, due dates, statuses, and a portfolio audit snapshot. Sample seeding is explicit and does not replace existing records. Demo records are simulated; user-entered records are not lender-verified. EMI payment collection and repayment history are not connected.
- [~] Backend production hardening remains incomplete: real document upload/storage/OCR, real lender handoff, push notifications, human support, and production secret/database/deployment configuration are absent.

# 1. Complete mobile app feature list

## A. Authentication and user profile

Essential

- [x] Email/password login and registration — connected to `/api/auth`; session restoration validates against `/api/auth/me`.
- [ ] Phone/OTP login — the old phone flow is no longer active; the connected path uses email/password.
- [~] User profile and basic personal details — registration collects some details, but the profile screen is mostly hard-coded.
- [ ] Profile editing.
- [~] Session management — native token uses SecureStore and web uses AsyncStorage; restore checks `/api/auth/me`. Refresh/revocation is not implemented.
- [ ] Account deletion request.
- [x] Language selection — English, Hindi and Marathi are selectable and persist locally.
- [ ] PIN/biometric app lock — legacy phone/PIN screens are not part of active email auth.

## B. Onboarding and personalization

Essential

- [~] Welcome/sign-in screen introduces Sahayak; consent-based personalization onboarding is not implemented.
- [ ] Select preferred language: English, Hindi, Hinglish.
- [ ] Select accessibility preferences.
- [ ] Ask what the user needs help with.
- [ ] Explain how personal data will be used.
- [ ] Obtain purpose-specific consent.
- [ ] Let users skip optional onboarding questions.

## C. Main dashboard

Essential

[Novbank - Mobile Fintech Banking Overview Dashboard by Delibix on Dribbble](https://images.openai.com/static-rsc-4/a6psymyV7W1He0jPsXtzbI-sT1YKjpF_vmnTY_jLLzqRhiGcooag5NWGmRT9-yPsOB8HkZvC3nAQF3q1N4k_3o2_0FLPBKZVuarSSEWSzoWftSlBHay8kI3g80u2rqSkzEZmyQ7BD-x9KBrGlxsxn7qLrl-t0y8TKfyeiz4uKnY?purpose=inline)

[Smart Finance & Expense Tracking Mobile App UI UX Design by Aftabul Islam Samudro for Panze - UX Design Studio on Dribbble](https://images.openai.com/static-rsc-4/9YJH6cOrRD_em5vBqDQtMqWXYY3N-lEblNAPSfcCYnic4FpmsL2_cZfJE14r-EKGOnpJ1m4Pkplnu8pLWfjd2da0og5ves5WlT7aZS4R8S1AaUhlV2j4VC7CUlMFEpSUFKyzUc-OPiozLgOFvlzsZmy2bXdGQbvBI4pgi8zGA4Y?purpose=inline)

[Spendly - Finance Dashboard Mobile Responsive by Dipa Product for Dipa Inhouse on Dribbble](https://images.openai.com/static-rsc-4/7aSWvt3tR3K5yjqb9v8LuYbRn0gvjIiUrm6-oWXT7LZmIVJSGW-mrFUCMzeN8vIGkUG4PKhROC-9hf8w0dFC8jsUxziKDtjAK01DbMcxW8Feq7V_d6MhQbqRYRIhlhudZWLhHA96efqWzHsfyqg1Hsy5p3BUojHVeL3BchFGRRw?purpose=inline)

11

The dashboard should show everything important in one place:

- [~] Welcome message — present, but displays a hard-coded Ubanku demo user.
- [~] AI assistant shortcut — backend chat endpoint is connected; external processing is disabled.
- [x] Start a new financial journey — creates a backend loan-readiness record.
- [~] Continue an existing journey — restores cached per-user draft and fetches backend stage.
- [~] Application status — readiness stage is shown; lender application status does not exist.
- [~] Pending tasks — demo journey steps are shown; full backend checklist is not rendered.
- [~] Required documents — synthetic document choices are shown; there is no real document upload.
- [~] Recent activity — shows persisted authenticated Stripe top-up orders; there is no complete account activity feed, and send/withdraw are blocked until a supported transfer provider is integrated.
- [~] Cashback and referral cards are demo-only labels; no reward accrual or redemption service exists.
- [ ] Important reminders.
- [ ] Help and support.

## D. AI financial assistant

Core feature

[Nexwealth - AI Assistant Finance Mobile Apps by Illiyin Studio on Dribbble](https://images.openai.com/static-rsc-4/LC4_0xuVt6Lpj3w6Wc1filZ0DzKZsYxuhBwS15GvU1S-qU7RQuiMisF-fF81PrbVISK5a1ssCm1Uti8GiH6D2FW7CZM5qTcsfaK3b_5SCTTNN6eMMqY9KhKfkZiQ1DDM6_uWLj8wLJNC49_EgkrIJZnsBSc5xOt8QjO6uxT6Au4?purpose=inline)

[Smart Financial Assistant with Natural Chat by Md Emon on Dribbble](https://images.openai.com/static-rsc-4/rOYwSUHJnXIGFO3rZHPtu5TW3GZVqIDWFe1hNzJRywE6FkBIvTt3R5KW6HHsl5jWxRvL9Qv1FJxkT3FyZn9yjj5HnhC_ZrxKMx88EMXevJ0IDYAbLAowHP8ojF0SdMBJqm-3O9u8eS92gc7n7CNmdQ48atgPtZ1EqwQF-8vnGQI?purpose=inline)

[AI Assistant Mobile App - Smart Voice & Chat Experience by Tonmoy Das on Dribbble](https://images.openai.com/static-rsc-4/3uy7QfFng6cFdxXaylwC04_k4pLxvHVGZT2YyAGIuorGl_rr_WTh9mN_dHNpODgNDUK2CoRCkj1yxAoPfZY8rpRiR22X0KuJBRfgHWRGoHW8r70gZh0_rYu57ife57iqe5K13Khb_vmqorsNJxZc4TKGCmBk2Dx8fSFiBxFOLdA?purpose=inline)

12

This is the main interaction point of Sahayak AI.

Features:

- [~] Text-based conversation — chat calls `/api/chat`; external processing remains disabled by default, so responses use the deterministic fallback unless provider configuration and consent allow AI processing.
- [~] Voice input, speech-to-text, and text-to-speech — the chat screen is connected to the backend voice pipeline; provider keys and external-processing controls are required for live processing.
- [~] AI response language — English, Hindi, and Marathi can be selected from chat or language settings; the persisted chat preference is sent to text, transcription, and speech output paths.
- [~] Context-aware help can receive one owned loan journey or verified Stripe order reference; it has no multi-turn memory or general follow-up state.
- [ ] Explain financial terms in simple language.
- [ ] Guide users step by step.
- [ ] Summarize conversations.
- [~] Chat has no persistent conversation history. For one turn, the app can attach an owned journey or verified payment-order reference; external AI gets payment context only after separate consent and server flags are enabled.
- [ ] Suggest relevant next steps.
- [ ] Ask for clarification when information is missing.
- [ ] Transfer the user to human support.

Example ( [~] the connected demo supports journey preparation and deterministic fallback responses; it does not run the full AI dialog below):

User: "Mujhe ₹2 lakh ka personal loan chahiye. Meri salary ₹30,000 hai."

Sahayak AI:

1. Understands the user's requirement.
2. Asks about employment and existing obligations.
3. Explains relevant loan requirements.
4. Calculates illustrative EMI.
5. Helps prepare the application.

The AI must not promise loan approval or make lending decisions. [~] Backend guardrails and a safe fallback are present; live AI, voice, conversation history, and human escalation are not connected.

## E. Financial journey modules

Core feature

Build each financial service as an independent module, sharing common components such as the assistant, documents, consent and journey tracking.

[Loan Application designs, themes, templates and downloadable graphic elements on Dribbble](https://images.openai.com/static-rsc-4/xzeiYx3tMvygxO8e06F4lrtkjr2QMxVWRgWBfYANyyug0DzIFri5YU4UK3Q750mO00u4VOZP7PnWB2uPB_tiyeUGLRKv7dN9_bzi_sPSJhSKYRmjzbyiXA_Acn3snT0-S6O1SAisU56JnM9KLamyhEeCuJXcATezY3IBLYZPkHk?purpose=inline)

1\. [~] Personal loan assistance

Build first

The connected demo supports a database-backed synthetic offer catalogue, deterministic EMI, a backend readiness journey, synthetic document preflight and a consented readiness handoff. Catalogue filtering uses loan amount, tenure and supplied income criteria; catalogue records can be maintained by an administrator with rate history and source metadata. The development seed is illustrative, not live lender data. Real eligibility decisions, file upload, and lender application submission are not implemented.

[Best Insurance in Pittsburgh Pennsylvania | Compare Quotes & Save](https://images.openai.com/static-rsc-4/opSsq0m5AXU5ySMjvyZC4LzsFZt190L-m2P-f15vv5_vSLJ2trwRCzJqDZeJKJZUrFTk3B97yN6U4iHk8E7sBxDirwFvSs_H-ACtKbTE8FXfehfpYO-9we9KNbqM84pEao7Ba4NBOxLcJ7zv0r8A2Zy4dqne40U9Y0IteqaQI9s?purpose=inline)

2\. [ ] Insurance assistance

Later phase

Understand coverage, compare policy terms, check exclusions and organize claim documents.

[Mobile Identity - Instant Identity Verification & KYC Platform | LegAn](https://images.openai.com/static-rsc-4/FbdwKHJeZSrS3ubsedQPUc5ToYl8esepzVHt3N6-DvsDjJY2_D81-5id3RUhHn987ndRJo62O62le0x4MFmWNmL-AyP3Ut0IG27ARcbTmu8sgLW5mxzevSX3wTZc2u9cUxJMkJ_tf4KnryeMTpSKp-DmXFSlcjeAoqDcoEFd_2I?purpose=inline)

3\. [ ] KYC assistance

Later phase

KYC checklist, document preparation, verification guidance and status tracking through authorized providers.

[Making payments online isolated cartoon vector illustrations.](https://images.openai.com/static-rsc-4/gltYgFcom34ZQ-qWz8dA8-a5_lYkOwKPczmislho7orgTI71ircBw6nZTeNOwCjediyhOv3h7COmtOlemBCx7wW8SdMmL02W5QXss90UprKUxIRbkBIlLJl0FsDW7ga3qHfJLaRR39siLrtv9UlZ9m4u7fA7RSS6_B2whqjMyIAlEoCC0sDXhiaW53kUjsx5?purpose=inline)

4\. [~] Payments assistance

Later phase

Explain payment issues, organize transaction references, guide users through authorized support and dispute processes. Sahayak can explain the server-verified status of a Stripe top-up; there is no dispute workflow, payment support ticket, refund handling, or human escalation.

**Payments/Paytm-style app scope:** The app has a Stripe test checkout ledger and a separate simulated demo wallet. The demo wallet supports account-to-account sample transfers and history but has no cash value and cannot be withdrawn. It is never funded from Stripe. Actual merchant collection, UPI, bank transfer, refunds and settlement reporting are not connected. Stripe Connect must not be assumed to support P2P or wallet cash-out; use it for marketplace seller settlement only if Stripe gives written approval for this India platform and exact flow. History labels demo events as simulated and Stripe orders separately. See the [Stripe money-movement research plan](docs/stripe-money-movement-research-plan.md).

**Demo versus actual finance:** Synthetic loan accounts, EMI schedules, “EMI paid” events and wallet activity can be persisted in the database for a walkthrough only when explicitly labeled simulated and not represented as money received, loan disbursed, repayment made, or funds available. Stripe should be reserved for an actual approved merchant charge; the database should store its verified provider status. For real lending and EMI repayment, the regulated lender and its authorized payment channel remain authoritative. See the [Stripe-versus-database feature matrix](docs/stripe-money-movement-research-plan.md#capability-decision-matrix-stripe-or-demo-database).

**Credit-score boundary:** The authenticated score endpoint and score-related chat response return only a clearly named Sahayak demo payment-behaviour indicator based on explicit synthetic repayment records; wallet top-ups are excluded. It is not a CIBIL score, creditworthiness assessment or loan-approval prediction. The current app has no bureau integration or verified loan repayments, so the expected result is insufficient data. A real CIBIL score requires an authorized bureau/data integration and valid user consent. See [CIBIL's score/report description](https://www.cibil.com/faq-brochure).

[Spendly | A mobile app for monitoring finances :: Behance](https://images.openai.com/static-rsc-4/53bByCtYYQyLAOmWramwQTs9zZfsiIfE1VEKczHrXaJWtqPBh4dnsim8j0F3EBQLbaHALrgO1jBODoqMcccaFcz0l8q3xEfcXjkDu31Lq_9of3h6qwTlw_Y4p1Qk95uVuBj2Gw70CeV_dV8W58zN6ybsN1GLgozdwCICmctzCdk?purpose=inline)

5\. [ ] Personal finance management

Later phase

Budget planning, savings goals, expense organization, reminders and financial education.

## F. Financial calculators and tools

Essential

- [~] Personal loan EMI calculator — server calculation is connected to synthetic offers and uses deterministic Decimal arithmetic; values are indicative only.
- [ ] Loan affordability estimator.
- [ ] Interest calculator.
- [ ] Total repayment calculator.
- [ ] Loan tenure comparison.
- [ ] Monthly budget planner.
- [ ] Savings goal calculator.
- [ ] Insurance premium comparison when reliable product data is available.

All financial calculations use the deterministic backend calculator; offer data is synthetic and no lender quote is obtained.

## G. Document management

Essential

[DoNotPay Document Scanner Preview](https://images.openai.com/static-rsc-4/BZ7HYfcuARHPdxKntYTynGgIXSG__BmGBUWdRi-1b9WB0qvXCD-EXRxl8QCAaQS4ej93vTOjKiWol5Kc9weAdAAY8hMC9w3rVIgDXy8a6c2a8WnGkJp-kBZWDQc5u2sT3nQ_4TECjFfNdo2Uc2sOM4nuKj2795ns1vs79cl0XMU?purpose=inline)

[The Document Scanner RTU UI v.2.0 is here - Scanbot SDK](https://images.openai.com/static-rsc-4/FtM7IFObMRtBRmIO-mE8KRg_QsupzidfTsRnpAlaohpdvAvBvholsMim6CACFJqyEHLH2dCawWCzuHled4T3G86NlzFuqam4-zXHqIPNvMG_MtB3Z7K7ZB1twt3iqPhqUUtvwhj5CXhshClUyIyaJPb0w0G4U9qHTqKSNgsxsL8?purpose=inline)

[Control Spend with Intake-to-Procure | Zip](https://images.openai.com/static-rsc-4/OHllxEOx6UngIfSg7y7sdFJ_R3jaPCdYgCELuXNiFnN4F4PofFaTCzvDWul4mSFfZYBZUL_IZO_DoFQ4crKS7vqdBadQ4dL_CryVASs4hhIcg5D_aQzbhC7uLuqRSRBz3IkAvn3AhieEuZd4tNT-nLUtCVIlVWQWPMUFJ1P0OAk?purpose=inline)

7

- [~] Synthetic document preflight/confirmation is connected for demo records; actual files are not uploaded.
- [ ] Upload documents from phone storage. The current journey has a synthetic document-type checklist only.
- [ ] Camera-based document scanning.
- [ ] PDF and image support.
- [ ] File type and size validation.
- [ ] Upload progress and retry.
- [~] Backend synthetic OCR extraction works against generated values only.
- [ ] Real OCR-based data extraction from user files.
- [~] Extracted information review — generated values can be confirmed through the backend API; an editable field-review UI is not implemented.
- [ ] Allow users to correct extracted values in the mobile UI.
- [~] Missing-document checklist — backend journey response has a checklist; the mobile view does not render all backend checklist items.
- [ ] Document expiry reminders where relevant.
- [ ] Secure document storage.
- [ ] Delete uploaded documents.
- [ ] Show document processing status.

Important: OCR results must be treated as unverified until the user reviews them. [~] Only synthetic records are generated; no user file is uploaded or verified.

## H. Application management

Essential

- [~] Create an application readiness journey — server state persists in backend SQLite; client keeps an offline cache.
- [~] Save progress — core journey state persists server-side; income/employment details remain in the per-user local cache.
- [~] Resume an incomplete readiness journey — backend journey ID/stage and local per-user draft are restored; the server journey is fetched when resuming.
- [ ] Pre-fill verified information.
- [~] Edit application details — readiness fields remain editable in the local draft.
- [~] Validate required fields — basic amount/income inputs and final demo consent; no lender schema validation.
- [~] Generate a readiness summary — review screen combines cached inputs with backend offer/EMI/stage; it is not a lender application.
- [~] Show missing information — backend exposes missing items, but the mobile screen does not render its full checklist.
- [~] Ask for final confirmation — demo submission requires an explicit acknowledgement that no lender receives it.
- [~] Prevent duplicate handoff — the completed UI action is disabled; backend mutations accept idempotency keys, though the mobile client currently creates a new key per request.
- [~] Track journey stage — server FSM reaches `READY_FOR_HANDOFF`; no lender receives or decides an application.
- [~] Show readiness history — authenticated backend can list the user's readiness journeys; no lender application/loan account history exists.
- [ ] Show lender application status history.
- [ ] Show active loan accounts, repayment schedules, EMI collection and repayment history from a regulated lender.

The demo prepares a backend readiness handoff only. Authorized lender integration and actual application submission are not present.

## I. Notifications and reminders

Essential

- [ ] In-app notifications.
- [ ] Push notifications.
- [ ] Pending document reminders.
- [ ] Application status updates.
- [ ] Incomplete journey reminders.
- [ ] Upcoming payment reminders.
- [ ] Consent and security notifications.
- [ ] Notification preferences.

## J. Help and support

Essential

- [~] AI-powered help — deterministic journey/payment-status guidance is connected; live AI processing and human handoff are unavailable.
- [ ] Frequently asked questions.
- [ ] Raise a support request.
- [ ] Human support escalation.
- [ ] Support ticket tracking.
- [ ] Conversation summary for support staff.
- [ ] Report incorrect information.
- [ ] Report a technical issue.

## K. Settings, privacy and security

Essential

- [~] Language settings — app language and Sahayak chat response language each persist locally; chat supports English, Hindi, and Marathi selections.
- [ ] Accessibility settings.
- [ ] Notification preferences.
- [ ] Consent history and withdrawal.
- [ ] Privacy policy and terms.
- [ ] Active session management.
- [ ] Account deletion request.
- [ ] Data export request.
- [ ] Secure document access.
- [ ] Report suspicious activity.

# 2. Mobile app navigation structure

The target product calls for five tabs. The current signed-in app exposes Journey, Wallet and the legacy Ubanku home screen (`src/navigation/TabNavigator.tsx`).

Sahayak AI

WELCOME BACK

# Your financial journey, simplified.

Continue your journey

Personal loan · Documents pending

Progress

60%

Ask Sahayak AI

How can I help you today?

Loans

Explore assistance

Insurance

Understand coverage

Documents

Manage files

Calculators

Plan finances

Home

Explore

AI

Journeys

Profile

Conceptual mobile dashboard — a suggested layout, not a finished app. [ ] This Sahayak dashboard design is not implemented.

The signed-in navigation exposes the Sahayak journey dashboard, Wallet and the existing Ubanku home demo after email/password sign-in. A five-tab Sahayak navigation remains a future product target.

The five target tabs:

| Tab | Status | What it contains |
| --- | --- | --- |
| Home | [~] | A Sahayak readiness dashboard exists; wallet/home demo surfaces remain. |
| Explore | [ ] | Loans, insurance, KYC, finance tools |
| AI | [~] | Guardrailed backend text chat is embedded in the journey dashboard; no dedicated assistant tab or voice. |
| Journeys | [~] | Backend loan readiness journey and synthetic documents; no lender applications. |
| Profile | [~] | A Ubanku user menu exists; profile/settings/support actions are mostly placeholders. |

# 3. Features required beyond the UI

A financial app needs more than screens. These backend capabilities are equally important.

| Backend module | Status | Responsibility |
| --- | --- | --- |
| Authentication | [x] | Email/password JWT auth, `/me` validation and bearer-protected journey calls. |
| User service | [ ] | Profile and preferences |
| Journey engine | [~] | Backend FSM and authenticated journey persistence are connected for demo readiness stages. |
| AI orchestration | [~] | Guardrailed chat endpoint connected; external provider processing disabled. |
| Knowledge service | [~] | Static RAG/policy material exists; no maintained verified live product catalogue or lender-specific terms |
| Calculator service | [~] | Deterministic EMI and synthetic offers are connected. |
| Document service | [~] | Synthetic OCR preflight/confirmation only; no file upload/storage. |
| Application service | [~] | Readiness drafts, confirmations and handoff state; no lender submission service. |
| Notification service | [ ] | Push and in-app reminders |
| Consent service | [~] | Backend audit consent connected for synthetic document processing and demo handoff. |
| Audit service | [~] | Journey consent and payment-state audit records exist; there is no unified user-facing activity timeline |
| Support service | [ ] | Human escalation and ticket tracking |
| Admin service | [ ] | Operational review and product management |

### API contract alignment

The mobile client follows the routes and schemas currently implemented in `backend/app`. The architecture contract at `../docs/architecture/api-contracts.md` is an older, unreconciled specification. Examples of drift include `/api/financial/offers` vs `/api/offers`, `/api/financial/calculate` vs `/api/emi`, journey payload names (`preferred_tenure_months`/`purpose` vs `tenure_months`/`stated_purpose`), stage field names, synthetic JSON document preflight vs multipart file upload, and `/api/chat` vs `/api/chat/message`. Update that shared contract to the runtime API before another client integrates or production endpoints are designed.

# 4. Non-functional requirements

These are easy to overlook, but they matter if you want the project to be production-ready.

- [~] Security: native token storage uses SecureStore and journey APIs are authenticated; local demo uses HTTP, lacks refresh/revocation and needs production security review.
- [~] Privacy: document, handoff and optional payment-context consent exist; full consent history, data export/deletion and policy UX are missing.
- [~] Reliability: payment orders and wallet credits have idempotency/uniqueness protections; journey retry, recovery and reconciliation UX remain incomplete.
- [~] Performance: the Expo web app builds and runs; pagination and background document processing are absent.
- [~] Accessibility: some controls have labels, but systematic screen-reader, keyboard and voice support is not implemented.
- [~] Offline/recovery: a per-user local draft cache exists; server operations require connectivity and retry/reconciliation UX is incomplete.
- [~] Observability: errors are logged to the console; error tracking, metrics and audit trails are absent.
- [~] AI safety: underwriting guardrails, grounded retrieval and citation/number checks exist; live AI is off and uploaded-document prompt-injection handling is not exercised because real documents are not connected.
- [~] Verification status (2026-10-31): backend suite passed 176 tests, Jest passed 9 tests, changed payment screens have no ESLint errors, and Expo web export succeeded after send/withdraw shutdown. TypeScript still reports errors in legacy components/screens outside this payment change. No native device E2E or live Stripe round-trip has been run.

# 5. What I recommend building first

Don't build all five financial journeys immediately. Make the first loan journey excellent, then reuse its infrastructure for other services.

## Phase-wise implementation

1. Phase 1 — Mobile foundation — [~] Email auth, session validation, Sahayak API wiring and local cache are connected; onboarding consent and broader profile settings remain.

   Start here
   - [~] Authentication and onboarding
   - [~] Language selection is implemented; purpose-specific consent remains missing
   - [~] Dashboard and bottom navigation (Sahayak Journey, Wallet and legacy Ubanku demo tabs)
   - [~] Profile and settings (language works; profile/support entries remain placeholders)
2. Phase 2 — AI assistant — [~] Backend text chat is wired with external processing disabled; full conversational AI remains incomplete.
   - [~] Text chat (safe fallback only); voice
   - [ ] Multilingual support
   - [ ] Conversation history
   - [ ] Context-aware guidance
3. Phase 3 — Loan journey — [~] Backend readiness pipeline is connected; lender integration and full application submission remain.
   - [~] Basic needs capture and synthetic offer selection
   - [~] Synthetic offer comparison and backend EMI
   - [~] Requirements checklist (backend response; incomplete mobile display)
4. Phase 4 — Document intelligence — [~] Synthetic preflight only.
   - [ ] Upload and camera scanner
   - [~] Synthetic OCR and data extraction
   - [ ] User correction and verification
   - [ ] Secure document management
5. Phase 5 — Application management — [~] Readiness record save/resume, summary and explicit demo handoff are connected.
   - [~] Readiness form preparation, save/resume, summary and explicit confirmation
   - [~] Backend `READY_FOR_HANDOFF` stage; no lender submission/status tracking
6. Phase 6 — Production readiness — [~] Some security, audit, idempotency and staging-payment foundations exist; production operations and verification are not complete.
   - [ ] Notifications and support
   - [ ] Security and privacy testing
   - [ ] Failure recovery
   - [ ] Analytics and admin dashboard
7. Phase 7 — Expansion — [~] Stripe-hosted top-up and verified payment-status explanation are implemented in code; the Stripe webhook round trip still needs environment verification. Refunds/disputes, insurance, KYC, budgeting and savings are not implemented.
   - [ ] Insurance
   - [ ] KYC
   - [~] Verified Stripe top-up status help only; support and dispute assistance remain unimplemented
   - [ ] Budgeting and savings

# 6. Suggested technology stack

| Layer | Recommendation | Current status |
| --- | --- | --- |
| Mobile app | React Native + Expo | [x] Expo support and web export are configured. |
| Backend | Python + FastAPI | [x] Included in `backend/`; local SQLite demo. |
| Database | SQLite local demo | [~] Used by backend; production PostgreSQL deployment is not configured. |
| Authentication | FastAPI JWT email/password | [~] Connected for demo; no refresh-token or phone OTP flow. |
| Document storage | Supabase private Storage | [ ] Not configured. |
| AI orchestration | FastAPI guardrailed chat route/provider abstraction | [~] Route connected; external processing disabled in demo. |
| AI providers | Backend provider adapters | [~] Code exists; credentials/rollout are disabled and mobile does not enable external processing. |
| Stripe | Authenticated backend Checkout Session + hosted checkout + signed webhook | [~] Test/demo plumbing and order history; real provider round-trip remains unverified. Live wallet/lending is fail-closed pending explicit written Stripe approval. |
| OCR | Synthetic backend preflight | [~] Demo-generated values only; no real uploaded files. |
| Push notifications | Expo Notifications | [ ] Not implemented. |
| Admin dashboard | React + Vite | [ ] Not found. |
| Hosting | Vercel for web/admin, suitable FastAPI hosting for backend | [ ] No deployment configuration found. |

Keep the mobile app independent of the AI provider. The app should call your FastAPI backend, and FastAPI should select the AI model. That way, you can change providers without updating the mobile app.

## My final recommendation

For the first Sahayak AI mobile release, I would target these 10 core deliverables:

1. [~] Email authentication and session validation are connected; onboarding and account recovery remain incomplete.
2. [~] Backend text and voice chat support English, Hindi, and Marathi; live external processing remains configuration- and consent-gated.
3. [~] Sahayak readiness dashboard is connected; full financial dashboard remains incomplete.
4. [~] Backend loan readiness journey and stage tracking are connected; no lender handoff integration.
5. [~] Backend synthetic-offer EMI calculator is connected; affordability estimator remains incomplete.
6. [~] Synthetic OCR preflight is connected; actual file upload/OCR/storage remains incomplete.
7. [~] Readiness preparation and review are implemented; lender application preparation is missing.
8. [~] Demo backend stage tracking is implemented; lender application status tracking is missing.
9. [ ] Notifications and human support.
10. [~] Privacy, consent and security controls — selected audit/consent protections exist; production controls, deletion/export and full review remain.

This gives you a complete, demonstrable product rather than a collection of disconnected screens.

The most important design principle: Every journey should be resumable. The current demo restores backend readiness stages and lists prior readiness records; reliable recovery after interrupted network operations still needs retry and reconciliation behavior. Before building real collection, lending, or repayments, choose the regulated payment/wallet and lending partners and connect their sandbox contracts. RBI digital lending rules require the regulated entity to retain responsibility, assess creditworthiness, provide disclosures/KFS, and control loan disbursal/repayment flows; this demo does not do that. See [RBI Digital Lending Directions, 2025](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12848&Mode=0). Stripe's [India payment-method support](https://support.stripe.com/questions/supported-payment-methods-currencies-and-businesses-for-stripe-accounts-in-india?locale=en-GB) excludes local methods such as UPI and its [restricted-business policy](https://stripe.com/in/legal/restricted-businesses) treats lending, money transmission, and stored-value services as restricted/prohibited categories. Obtain written Stripe approval before any live use.
