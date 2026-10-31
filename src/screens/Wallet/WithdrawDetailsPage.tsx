import React from 'react';
import PaymentUnavailablePage from './PaymentUnavailablePage';

const WithdrawDetailsPage = () => (
  <PaymentUnavailablePage
    title="Withdrawal unavailable"
    message="No Stripe payout or bank withdrawal has been configured. This screen cannot send funds or report a withdrawal as successful."
  />
);

export default WithdrawDetailsPage;
