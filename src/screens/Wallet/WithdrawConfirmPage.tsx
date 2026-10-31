import React from 'react';
import PaymentUnavailablePage from './PaymentUnavailablePage';

const WithdrawConfirmPage = () => (
  <PaymentUnavailablePage
    title="Withdrawal not submitted"
    message="No Stripe payout was created and no funds were sent to a bank or UPI account."
  />
);

export default WithdrawConfirmPage;
