import {useNavigation, useFocusEffect} from '@react-navigation/native';
import React, {useCallback, useState} from 'react';
import {ActivityIndicator} from 'react-native';
import {Center, Text, VStack} from 'native-base';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UText from '../../components/atoms/UText';
import UPressableTransaction from '../../components/molecules/wallet/UPressableTransaction';
import iTransaction from '../../interfaces/Wallet/iTransaction';
import {useLanguage} from '../../contexts/LanguageContext';
import {useAuth} from '../../contexts/AuthContext';
import {
  getWalletPaymentHistory,
  getDemoWalletEntries,
  WalletPaymentHistoryItem,
  DemoWalletEntry,
} from '../../services/sahayakApi';

const WalletTransactionsPage = () => {
  const navigation = useNavigation();
  const {t} = useLanguage();
  const {authToken} = useAuth();
  const [orders, setOrders] = useState<WalletPaymentHistoryItem[]>([]);
  const [demoEntries, setDemoEntries] = useState<DemoWalletEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      setError('');
      if (!authToken) {
        setOrders([]);
        setDemoEntries([]);
        setLoading(false);
        setError('Sign in to view your payment history.');
        return () => {
          active = false;
        };
      }
      Promise.all([
        getWalletPaymentHistory(authToken),
        getDemoWalletEntries(authToken),
      ])
        .then(([items, entries]) => {
          if (active) {
            setOrders(items);
            setDemoEntries(entries);
          }
        })
        .catch(() => {
          if (active) {
            setError(
              'Could not load payment history. Check your connection and try again.',
            );
          }
        })
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
      return () => {
        active = false;
      };
    }, [authToken]),
  );

  const transactions: iTransaction[] = [
    ...orders.map(order => ({
      transactionType: 'Deposit',
      transactionName: 'Wallet top-up',
      transactionDate: order.created_at,
      transactionStatus: order.status,
      transactionId: order.order_id,
      transactionPaymentMethod: order.provider.toUpperCase(),
      transactionValue: Number(order.amount_rupees),
    })),
    ...demoEntries.map(entry => ({
      transactionType: entry.entry_type === 'DEBIT' ? 'Send' : 'Receive',
      transactionName: entry.description,
      transactionDate: entry.created_at,
      transactionStatus: 'SIMULATED · COMPLETED',
      transactionId: entry.transaction_id,
      transactionPaymentMethod: 'DEMO WALLET',
      transactionValue: entry.amount_paise / 100,
    })),
  ];

  return (
    <UBasicScrollableNavigationWrapper
      onPressBackButton={() => navigation.goBack()}>
      <UText title center my={3}>
        {t('transactionHistory')}
      </UText>
      <VStack space={4} mt={5}>
        {loading ? (
          <Center py={10}>
            <ActivityIndicator />
            <Text mt={3}>Loading payment history…</Text>
          </Center>
        ) : null}
        {!loading && error ? (
          <Text color="error.600" textAlign="center" py={8}>
            {error}
          </Text>
        ) : null}
        {!loading && !error && transactions.length === 0 ? (
          <Text color="text.500" textAlign="center" py={8}>
            No payment or demo activity yet. Stripe test top-ups and simulated
            wallet activity will appear here.
          </Text>
        ) : null}
        {!loading &&
          !error &&
          transactions.map(transaction => (
            <VStack key={transaction.transactionId} space={1}>
              <UPressableTransaction transaction={transaction} />
              <Text color="text.500" fontSize="xs" ml={12}>
                {transaction.transactionStatus} · {transaction.transactionId}
              </Text>
            </VStack>
          ))}
        <Text color="text.500" fontSize="xs" textAlign="center" mt={4}>
          Demo wallet entries debit one demo account and credit another. These
          records are simulated and do not represent real money, bank
          statements, or loan repayments.
        </Text>
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default WalletTransactionsPage;
