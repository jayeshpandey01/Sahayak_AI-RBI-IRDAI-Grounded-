import React from 'react';
import PaymentUnavailablePage from './PaymentUnavailablePage';

const WithdrawPage = () => (
  <PaymentUnavailablePage
    title="Withdraw money"
    message="Stripe wallet top-ups in this demo are not transferable stored value. Bank withdrawals and payouts are not connected, so no funds can be sent to a bank or UPI account."
  />
);

export default WithdrawPage;
