import React, {useCallback, useState} from 'react';
import {Alert, Button, HStack, Input, Text, VStack} from 'native-base';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UText from '../../components/atoms/UText';
import {useAuth} from '../../contexts/AuthContext';
import {addDemoWalletFunds, getDemoWallet, DemoWalletInfo} from '../../services/sahayakApi';
import {apiErrorMessage} from '../../services/apiClient';
import {formatRupees} from '../../utils/currency';
import {clearDemoWalletOperationKey, getDemoWalletOperationKey} from '../../services/demoWalletIdempotency';

const FundDemoWalletPage = () => {
  const navigation = useNavigation<any>();
  const {authToken, user} = useAuth();
  const [wallet, setWallet] = useState<DemoWalletInfo | null>(null);
  const [amount, setAmount] = useState('1000');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);

  const refresh = useCallback(async () => {
    if (!authToken) return;
    try {
      const current = await getDemoWallet(authToken);
      setWallet(current);
      setError('');
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    }
  }, [authToken]);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

  const addFunds = async () => {
    const value = Number(amount);
    if (!authToken || !Number.isFinite(value) || value <= 0 || value > 10000) {
      setError('Enter an amount from ₹1 to ₹10,000.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const operation = `fund:${user?.id || 'unknown'}:${value.toFixed(2)}`;
      const key = await getDemoWalletOperationKey(operation);
      const result = await addDemoWalletFunds(authToken, value, key);
      clearDemoWalletOperationKey(operation).catch(() => undefined);
      setWallet(current => ({
        wallet_code: current?.wallet_code || '',
        display_name: current?.display_name || '',
        balance_paise: result.balance_paise,
        currency: 'INR',
        is_simulation: true,
      }));
      setComplete(true);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={() => navigation.goBack()}>
      <VStack space={5} px={4} py={6}>
        <UText title center>Add demo funds</UText>
        <Alert status="warning" borderRadius="lg">
          <VStack space={1}>
            <Alert.Icon />
            <Text color="text.800">
              These funds are simulated and have no cash value. You can transfer them only between demo wallets.
            </Text>
          </VStack>
        </Alert>
        <VStack space={2} alignItems="center">
          <Text color="text.600">Demo balance</Text>
          <UText title>₹ {formatRupees((wallet?.balance_paise || 0) / 100)}</UText>
        </VStack>
        {complete ? (
          <VStack space={4}>
            <Alert status="success" borderRadius="lg">
              <Text>Demo funds added. New balance: ₹ {formatRupees((wallet?.balance_paise || 0) / 100)}.</Text>
            </Alert>
            <Button onPress={() => navigation.goBack()}>Back to wallet</Button>
          </VStack>
        ) : (
          <VStack space={4}>
            <Text color="text.700">Amount to add (up to ₹10,000 per action)</Text>
            <Input value={amount} onChangeText={setAmount} keyboardType="decimal-pad" placeholder="1000.00" />
            <HStack space={2}>
              {[500, 1000, 5000].map(value => (
                <Button key={value} flex={1} variant="outline" onPress={() => setAmount(String(value))}>
                  ₹{value.toLocaleString('en-IN')}
                </Button>
              ))}
            </HStack>
            {error ? <Text color="error.600">{error}</Text> : null}
            {error ? <Button variant="outline" onPress={refresh}>Retry wallet connection</Button> : null}
            <Button onPress={addFunds} isLoading={busy} isDisabled={busy || !authToken}>
              Add simulated funds
            </Button>
          </VStack>
        )}
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default FundDemoWalletPage;
