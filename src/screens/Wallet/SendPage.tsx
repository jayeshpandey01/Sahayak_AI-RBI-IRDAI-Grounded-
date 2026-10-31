import React, {useCallback, useState} from 'react';
import {CameraView, useCameraPermissions} from 'expo-camera';
import {Alert, Button, FormControl, Input, Text, VStack} from 'native-base';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UText from '../../components/atoms/UText';
import {useAuth} from '../../contexts/AuthContext';
import {
  DemoWalletInfo,
  getDemoWallet,
  parseDemoWalletQr,
  sendDemoWalletFunds,
} from '../../services/sahayakApi';
import {apiErrorMessage} from '../../services/apiClient';
import {formatRupees} from '../../utils/currency';
import {clearDemoWalletOperationKey, getDemoWalletOperationKey} from '../../services/demoWalletIdempotency';

const SendPage = () => {
  const navigation = useNavigation<any>();
  const {authToken, user} = useAuth();
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [wallet, setWallet] = useState<DemoWalletInfo | null>(null);
  const [recipientCode, setRecipientCode] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [scanning, setScanning] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState<{recipient: string; amount: number; balance: number} | null>(null);

  useFocusEffect(useCallback(() => {
    let active = true;
    if (authToken) {
      getDemoWallet(authToken)
        .then(result => { if (active) setWallet(result); })
        .catch(requestError => { if (active) setError(apiErrorMessage(requestError)); });
    }
    return () => { active = false; };
  }, [authToken]));

  const handleBarcode = ({data}: {data: string}) => {
    const code = parseDemoWalletQr(data);
    if (!code) {
      setError('That QR is not a Ubanku demo wallet QR.');
      return;
    }
    setRecipientCode(code);
    setScanning(false);
    setReviewed(false);
    setError('');
  };

  const reviewTransfer = () => {
    const value = Number(amount);
    if (!recipientCode.trim() || !Number.isFinite(value) || value <= 0 || value > 100000) {
      setError('Scan or enter a demo wallet code and an amount from ₹0.01 to ₹1,00,000.');
      return;
    }
    setError('');
    setReviewed(true);
  };

  const confirmTransfer = async () => {
    const value = Number(amount);
    if (!authToken || !wallet) {
      setError('Sign in and load your demo wallet before sending.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const operation = `send:${user?.id || 'unknown'}:${recipientCode.trim().toUpperCase()}:${value.toFixed(2)}:${note.trim()}`;
      const idempotencyKey = await getDemoWalletOperationKey(operation);
      const result = await sendDemoWalletFunds(
        authToken,
        {recipient_wallet_code: recipientCode.trim().toUpperCase(), amount_rupees: value, note: note.trim() || undefined},
        idempotencyKey,
      );
      clearDemoWalletOperationKey(operation).catch(() => undefined);
      setWallet(current => current ? {...current, balance_paise: result.balance_paise} : current);
      setSent({recipient: result.recipient_name, amount: result.amount_paise, balance: result.balance_paise});
      setReviewed(false);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={() => navigation.goBack()}>
      <VStack space={5} px={4} py={6}>
        <UText title center>{sent ? 'Demo transfer complete' : 'Send demo funds'}</UText>
        <Alert status="warning" borderRadius="lg">
          <VStack space={1}>
            <Alert.Icon />
            <Text color="text.800">
              Simulated transfer between signed-in demo wallets. The server checks your balance, debits you, and credits the recipient atomically. No real money moves.
            </Text>
          </VStack>
        </Alert>

        {sent ? (
          <VStack space={4}>
            <Alert status="success" borderRadius="lg">
              <VStack space={1}>
                <Text fontWeight="700">Sent ₹{formatRupees(sent.amount / 100)} to {sent.recipient}</Text>
                <Text>New demo balance: ₹{formatRupees(sent.balance / 100)}</Text>
              </VStack>
            </Alert>
            <Button onPress={() => navigation.goBack()}>Back to wallet</Button>
            <Button variant="outline" onPress={() => navigation.navigate('Wallet' as never)}>View transaction history</Button>
          </VStack>
        ) : (
          <VStack space={4}>
            <Text textAlign="center" color="text.600">
              Available demo funds: ₹{formatRupees((wallet?.balance_paise || 0) / 100)}
            </Text>
            {scanning ? (
              <VStack space={3}>
                {cameraPermission?.granted ? (
                  <CameraView
                    style={{height: 260, width: '100%', overflow: 'hidden', borderRadius: 16}}
                    barcodeScannerSettings={{barcodeTypes: ['qr']}}
                    onBarcodeScanned={handleBarcode}
                  />
                ) : (
                  <Button onPress={requestCameraPermission}>
                    Allow camera to scan QR
                  </Button>
                )}
                <Button variant="outline" onPress={() => setScanning(false)}>Enter code instead</Button>
              </VStack>
            ) : (
              <VStack space={4}>
                <Button variant="outline" onPress={() => setScanning(true)}>Scan recipient QR</Button>
                <FormControl>
                  <FormControl.Label>Recipient demo wallet code</FormControl.Label>
                  <Input
                    value={recipientCode}
                    onChangeText={value => { setRecipientCode(value.toUpperCase()); setReviewed(false); }}
                    autoCapitalize="characters"
                    maxLength={24}
                    placeholder="UBK-XXXXXXXXXXXX"
                  />
                </FormControl>
                <FormControl>
                  <FormControl.Label>Amount (INR)</FormControl.Label>
                  <Input value={amount} onChangeText={value => { setAmount(value); setReviewed(false); }} keyboardType="decimal-pad" placeholder="0.00" />
                </FormControl>
                <FormControl>
                  <FormControl.Label>Note (optional)</FormControl.Label>
                  <Input value={note} onChangeText={setNote} maxLength={240} placeholder="Demo transfer note" />
                </FormControl>
                {reviewed ? (
                  <Alert status="info" borderRadius="lg">
                    <VStack space={2}>
                      <Text>Send ₹{formatRupees(Number(amount))} to wallet {recipientCode.trim().toUpperCase()}?</Text>
                      <Text>Your demo balance will be reduced immediately if you confirm.</Text>
                    </VStack>
                  </Alert>
                ) : null}
                {error ? <Text color="error.600">{error}</Text> : null}
                {reviewed ? (
                  <VStack space={2}>
                    <Button onPress={confirmTransfer} isLoading={saving} isDisabled={saving || !authToken}>Confirm demo send</Button>
                    <Button variant="outline" onPress={() => setReviewed(false)} isDisabled={saving}>Edit transfer</Button>
                  </VStack>
                ) : (
                  <Button onPress={reviewTransfer}>Review transfer</Button>
                )}
              </VStack>
            )}
          </VStack>
        )}
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default SendPage;
