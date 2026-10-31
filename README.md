Demo code open source with the authorization of Andrés F. Méndez, CEO of Ubanku Fintech.
# UbankuApp

UbankuApp is a React Native demo with a local FastAPI backend for the Sahayak AI loan-readiness journey. The demo wallet uses a separate simulated, account-scoped ledger for funding and QR transfers; it has no cash value. Stripe test Checkout is a separate optional payment-order demo and does not fund or debit the simulated wallet. This is not a production wallet, lender, or payment collection service. Real payments require a configured provider integration and approval for the intended use; real loans require a regulated lender integration.

See the [financial app readiness plan](docs/financial-app-readiness-plan.md) for the connected scope, partner requirements, and production acceptance plan.

The project adheres to the Atomic Design pattern to ensure a scalable and maintainable design system.

## Contact for Complete Fullstack Wallet Banking System and Custom Enterprise Technology Solutions

For inquiries about purchasing the complete or a customized wallet system, please reach out to:
- **Andrés F Méndez (CEO of Ubanku):**
  
    - [![LinkedIn](https://img.shields.io/badge/LinkedIn-andresfmendez-blue)](https://www.linkedin.com/in/andresfmendez/)
      
- **Daniel Sandoval (Software Engineer, Founding Team):**
  
    - [![LinkedIn](https://img.shields.io/badge/LinkedIn-danisando-blue)](https://www.linkedin.com/in/danisando/)

## Technologies

- **Frontend**:
  - React Native
  - TypeScript
  - JavaScript
  - Styled Components
    
- **Backend**:
  - FastAPI in `backend/` (included demo service)
  - **Testing**:
  - Jest

## Atomic Design

This project follows the Atomic Design methodology to create a consistent and scalable design system. Atomic Design structures our components into five distinct levels:
1. **Atoms**: The smallest building blocks, such as buttons, inputs, and labels.
2. **Molecules**: Combinations of atoms that form simple UI components, like a search form.
3. **Organisms**: Complex UI components made up of molecules and/or atoms, like a header or a card.
4. **Templates**: Page-level components that place organisms in a layout and articulate the design’s underlying content structure.
5. **Pages**: Specific instances of templates that display real content.

By organizing our components in this manner, we achieve a more maintainable and scalable codebase, allowing for easier updates and consistency across the application.

## Features Included in the Demo

- **Authentication Module**:
  - Backend email/password registration and login for the active Sahayak flow
  - JWT-backed session restoration and validation
  - Legacy phone/PIN screens remain in source but are not active or connected to this backend
    
- **Home Module**:
  - Dashboard with user overview
  - Navigation to other modules
    
- **User Module**:
  - Existing Ubanku profile and referral UI is demo/partial; profile editing is not connected to Sahayak accounts
    
- **Wallet Module**:
  - View the authenticated simulated demo balance, funding history, and account-to-account QR transfers
  - Demo sends debit the sender and credit the recipient atomically; insufficient balance is rejected
  - Optional Stripe test Checkout orders are kept in a separate payment ledger and are not spendable in demo transfers
  - Withdrawals and real transfers are unavailable

- **Loan Module**:
  - Create and resume synthetic loan readiness journeys and compare example offers/EMI calculations
  - Authenticated readiness history is not a record of approved or disbursed loans
  - No lender application, loan disbursement, repayment schedule, or real EMI collection is connected yet
    
- **Movements Module**:
  - View transaction history
  - Detailed view of individual transactions

## Screenshots

To give you a better idea of the application's interfaces, below are some key screenshots:

### Authentication Module

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/d493dce8-11a5-41ba-a1c9-d90267637af4" alt="Login Screen" width="300">
<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/88b98294-0d05-4511-bc96-93837f93e7c9" alt="Login step 1 Screen" width="300">

### Home Module

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/bc1f4f75-9cc3-4383-b7f0-220ef22e8e26" alt="Home Dashboard" width="300">


### User Module

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/f6075ade-f3f6-4ba3-a86c-bc33f2c11db5" alt="User Profile" width="300">
<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/13a23f7c-9e02-48ed-91dd-913854fc7ee7" alt="Referral System" width="300">

### Wallet Module

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/86db6acc-30fe-493b-b252-d076af03402c" alt="Wallet Balance" width="300">

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/17030d33-7756-47da-9290-1ede1d120bd3" alt="Add Funds" width="300">


## Movements Module

<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/6d5b7e08-8ceb-4720-abec-d33f2fd88cab" alt="Transaction History" width="300">
<img src="https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app/assets/56854119/ddec77f2-fb38-4c6c-97e0-7b6669aa50ba" alt="Transaction Details" width="300">


## Project Structure

```UbankuApp
├── App.tsx
├── Gemfile
├── Gemfile.lock
├── LICENSE
├── README.md
├── __tests__
│   └── App-test.tsx
├── android
│   ├── app
│   │   ├── build.gradle
│   │   ├── debug.keystore
│   │   ├── proguard-rules.pro
│   │   └── src
│   │       ├── debug
│   │       │   ├── AndroidManifest.xml
│   │       │   └── java
│   │       │       └── com
│   │       │           └── ubankuapp
│   │       │               └── ReactNativeFlipper.java
│   │       ├── main
│   │       │   ├── AndroidManifest.xml
│   │       │   ├── assets
│   │       │   ├── java
│   │       │   │   └── com
│   │       │   │       ├── MainActivity.java
│   │       │   │       └── MainApplication.java
│   │       │   └── res
│   │       └── release
│   │           └── java
│   │               └── com
│   │                   └── ubankuapp
│   │                       └── ReactNativeFlipper.java
│   ├── build.gradle
│   ├── gradle
│   │   └── wrapper
│   ├── gradle.properties
│   ├── gradlew
│   ├── gradlew.bat
│   ├── link-assets-manifest.json
│   └── settings.gradle
├── app.json
├── babel.config.js
├── index.js
├── ios
│   ├── Podfile
│   ├── Podfile.lock
│   ├── UbankuApp
│   │   ├── AppDelegate.h
│   │   ├── AppDelegate.mm
│   │   ├── Images.xcassets
│   │   ├── Info.plist
│   │   ├── LaunchScreen.storyboard
│   │   └── main.m
│   ├── UbankuApp.xcodeproj
│   ├── UbankuApp.xcworkspace
│   ├── UbankuAppTests
│   └── link-assets-manifest.json
├── metro.config.js
├── package-lock.json
├── package.json
├── react-native.config.js
├── src
│   ├── assets
│   ├── components
│   ├── contexts
│   ├── hooks
│   ├── interfaces
│   ├── navigation
│   ├── screens
│   ├── services
│   ├── theme
│   ├── types
│   └── utils
├── tsconfig.json
└── yarn.lock

```

## Installation

1. Clone the repository:
   
   ```sh
   git clone https://github.com/RogelioRichmanAstronaut/Ubanku-wallet-bank-app.git
   cd ubankuapp
   ```

3. Install dependencies with npm:

   ```sh
   npm ci
   ```

## Running with Expo

The app uses Expo SDK 58 and supports Expo Go on a physical Android or iOS
device, plus a browser preview. You do not need Android Studio or a local
Android SDK to run the app on a phone with Expo Go. Install a compatible Expo Go
client, then start the development server:

```sh
npm start
```

Scan the terminal QR code with Expo Go. To start Expo Go mode directly for
Android:

```sh
npm run android:expo
```

To run the browser preview:

```sh
npm run web
```

The legacy `npm run android` and `npm run ios` commands use the checked-in
React Native native projects; they require their respective native SDKs and are
not the Expo Go workflow. Building a standalone native app likewise requires
native build tooling or a configured remote build service.

Expo Go and the browser preview are for development/demo flows. The browser
keeps device-trust tokens in memory only; native Expo runs store them using
Expo SecureStore.

## API configuration

The FastAPI source is included in `backend/`. Start it in one terminal:

```sh
npm run backend:setup
npm run backend:start
```

Check `http://127.0.0.1:8000/health` and open `http://127.0.0.1:8000/docs`.
Keep `npm run backend:start` running while using the app. The app uses
`EXPO_PUBLIC_API_BASE_URL` and defaults to `http://127.0.0.1:8000` on iOS/web
or `http://10.0.2.2:8000` on the Android emulator. Using the explicit IPv4
loopback avoids `localhost` resolving to `::1` when Uvicorn is listening only
on IPv4. For a physical
device, set it to the development computer's LAN address, for example
`http://192.168.1.20:8000`, and keep both devices on the same network.

If registration reports “Could not connect” or a browser access-control error,
first confirm the backend terminal is still running and that
`http://127.0.0.1:8000/health` reports `database: connected`. A refused
connection can appear as a CORS error in browser developer tools even when the
origin configuration is correct.

If the demo wallet reports that its endpoint is missing, the app has reached an
older backend process or deployment. Restart/redeploy from this checkout and
confirm `/docs` lists `/api/v1/demo-wallet/me`, `/api/v1/demo-wallet/funds`, and
`/api/v1/demo-wallet/transfers`. Production databases must also apply pending
SQL files with `python backend/scripts/migrate.py apply` before using new tables.

To seed a local development account with the clearly simulated demo portfolio
(₹1 lakh demo wallet target, three example loan rows, and about 100 wallet
history entries), run `python backend/scripts/seed_demo_account_portfolio.py <account-email>`
from the repository root. The script refuses production and non-SQLite
databases; it does not create Stripe payments or real loan repayments.

Authentication uses the backend's email/password contract (`/api/auth/register`
and `/api/auth/login`). Native sessions use Expo SecureStore; web uses
AsyncStorage. The retired phone OTP screens are no longer the active sign-in
flow.

Stripe test Checkout top-ups require Stripe test keys in ignored `backend/.env` (or the
ignored repository-root `.env`, which the backend reads as a fallback):
`STRIPE_MODE=test`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, and
`STRIPE_WEBHOOK_SECRET`. Keep `STRIPE_LIVE_ENABLED=false`. Configure Stripe CLI
or a reachable HTTPS endpoint to forward `checkout.session.completed` events to
`/api/v1/webhooks/stripe`; without a valid signed webhook the app will not show
success or credit the wallet. Stripe Checkout returns to `ubankuapp://payment-return`
by default; set `STRIPE_RETURN_URL` for your demo host as needed. Send uses the
separate simulated demo wallet and does not call Stripe; real withdrawals and
payouts are unavailable. See the [Stripe migration plan](docs/stripe-migration-plan.md)
for setup and limitations. After a verified top-up, “Ask Sahayak” can explain
the server-verified payment status; sending that summary to external AI remains
disabled by default and requires separate consent and server flags. The Sahayak loan journey
uses backend email/password authentication, a database-backed synthetic offer catalogue,
deterministic server EMI, a persisted readiness journey, audited consent,
synthetic document preflight and a `READY_FOR_HANDOFF` demo state. The handoff
does not contact a lender or submit an application. Client inputs such as income
and employment remain in the per-user local cache.

For a stable local login across backend restarts, create `backend/.env` from
`backend/.env.example` and set a private `JWT_SECRET`. The development server
otherwise generates a process-local secret, so existing sessions expire when
the server restarts.

## Testing

Run the unit tests:

```sh
npm test
```

The Maestro E2E flows require the Maestro CLI and a standalone app installed on
a simulator/emulator. They are separate from Expo Go and require native build
tooling to create the app binary.

Run the backend connected journey flow with a pre-created demo account:

```sh
TEST_EMAIL=demo@example.test TEST_PASSWORD='StrongDemo123!' npm run e2e:journey:android
```

Build/install the app with the same `EXPO_PUBLIC_API_BASE_URL` used by the
simulator before running Maestro. The journey flow uses the backend's synthetic
offer catalogue and synthetic document preflight; it never uploads real files
or submits an application to a lender.

## License
This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE) file for details.

---
For more detailed information, please refer to the project documentation or contact the project maintainers.

[![GitHub](https://img.shields.io/badge/GitHub-RogelioRichmanAstronaut-181717?logo=github)](https://github.com/RogelioRichmanAstronaut)

*Developed by Daniel Sandoval.* 
