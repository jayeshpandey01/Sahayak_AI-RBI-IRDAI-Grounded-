import React, {useEffect, useRef, useState} from 'react';
import {ActivityIndicator, Linking, Pressable, Text, View} from 'react-native';
import {useNavigation, useRoute} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import {
  createStripeWalletTopup,
  refreshStripeWalletTopup,
  getServerWalletBalance,
} from '../../services/sahayakApi';
import {apiErrorMessage} from '../../services/apiClient';
import {formatRupees} from '../../utils/currency';

const wait = (ms: number) =>
  new Promise<void>(resolve => setTimeout(resolve, ms));

const DepositConfirmPage = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const {authToken, isAuthenticated} = useAuth();
  const amount = Number(route.params?.amount || 0);
  const [message, setMessage] = useState('Preparing secure Stripe checkout…');
  const [busy, setBusy] = useState(true);
  const [paid, setPaid] = useState(false);
  const orderId = useRef<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const start = async () => {
      if (started.current) return;
      started.current = true;
      if (!isAuthenticated || !authToken)
        throw new Error('Sign in before adding money to your wallet.');
      if (!Number.isFinite(amount) || amount < 1)
        throw new Error('Enter a valid top-up amount.');

      const order = await createStripeWalletTopup(
        authToken,
        amount,
        String(
          route.params?.operationId ||
            `wallet-topup-${Date.now()}-${Math.random()
              .toString(36)
              .slice(2, 10)}`,
        ),
      );
      if (!order.checkout_url || order.provider !== 'stripe')
        throw new Error('Stripe did not return hosted checkout details.');
      orderId.current = order.order_id;
      setMessage(
        'Stripe checkout opened. Complete the payment, then return here while we verify it.',
      );
      setBusy(false);
      await Linking.openURL(order.checkout_url);

      // The Stripe redirect/callback is not trusted. Poll our authenticated API;
      // only the signed webhook can move the order and wallet ledger to success.
      for (let attempt = 0; attempt < 90 && !cancelled; attempt += 1) {
        await wait(2000);
        if (!authToken || !orderId.current) return;
        try {
          const status = await refreshStripeWalletTopup(
            authToken,
            orderId.current,
          );
          if (status.status === 'SUCCEEDED') {
            await getServerWalletBalance(authToken);
            if (!cancelled) {
              setPaid(true);
              setMessage(
                'Payment verified. Your wallet balance has been refreshed.',
              );
            }
            return;
          }
          if (
            [
              'FAILED',
              'CANCELED',
              'EXPIRED',
              'RECONCILIATION_REQUIRED',
            ].includes(status.status)
          ) {
            if (!cancelled)
              setMessage(
                status.status === 'RECONCILIATION_REQUIRED'
                  ? 'Payment needs support review. No wallet credit was applied.'
                  : 'Stripe did not complete this payment. No wallet credit was applied.',
              );
            return;
          }
        } catch {
          /* Retry while the Stripe webhook/status is still pending. */
        }
      }
      if (!cancelled)
        setMessage(
          'Payment status is still pending. Return to the wallet and check again shortly.',
        );
    };

    start().catch(error => {
      if (!cancelled) {
        setMessage(apiErrorMessage(error));
        setBusy(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [amount, authToken, isAuthenticated, route.params?.operationId]);

  const done = () => navigation.navigate('Tabs', {screen: 'WalletTab'});
  const askSahayak = () =>
    navigation.navigate('Tabs', {
      screen: 'Home',
      params: {paymentOrderId: orderId.current},
    });
  return (
    <View
      style={{
        flex: 1,
        padding: 24,
        justifyContent: 'center',
        backgroundColor: '#f5fbfa',
      }}>
      <View
        style={{
          padding: 24,
          borderRadius: 18,
          backgroundColor: 'white',
          gap: 14,
        }}>
        <Text style={{fontSize: 24, fontWeight: '700', color: '#143f3c'}}>
          {paid ? 'Deposit complete' : 'Stripe wallet deposit'}
        </Text>
        <Text style={{fontSize: 16, color: '#334155'}}>
          Amount: ₹{formatRupees(amount)}
        </Text>
        {busy ? <ActivityIndicator color="#087f72" /> : null}
        <Text
          accessibilityRole="alert"
          style={{fontSize: 15, color: paid ? '#087f72' : '#475569'}}>
          {message}
        </Text>
        {!busy ? (
          <Pressable
            onPress={done}
            style={{
              backgroundColor: '#087f72',
              padding: 14,
              borderRadius: 12,
              alignItems: 'center',
            }}>
            <Text style={{color: 'white', fontWeight: '700'}}>
              Return to wallet
            </Text>
          </Pressable>
        ) : null}
        {paid ? (
          <Pressable
            onPress={askSahayak}
            style={{padding: 12, alignItems: 'center'}}>
            <Text style={{color: '#087f72', fontWeight: '700'}}>
              Ask Sahayak about this payment
            </Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
};

export default DepositConfirmPage;
