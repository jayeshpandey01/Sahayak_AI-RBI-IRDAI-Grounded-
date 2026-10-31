import React, {useCallback, useState} from 'react';
import {Button, Share, Text} from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import {VStack} from 'native-base';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UText from '../../components/atoms/UText';
import {useAuth} from '../../contexts/AuthContext';
import {DemoWalletInfo, getDemoWallet} from '../../services/sahayakApi';
import {apiErrorMessage} from '../../services/apiClient';

const ReceiveDemoMoneyPage = () => {
  const navigation = useNavigation<any>();
  const {authToken, user} = useAuth();
  const [wallet, setWallet] = useState<DemoWalletInfo | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true);
    if (!authToken) {
      setError('Sign in to view your demo receive QR.');
      setLoading(false);
      return () => { active = false; };
    }
    getDemoWallet(authToken)
      .then(result => { if (active) { setWallet(result); setError(''); } })
      .catch(requestError => { if (active) setError(apiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [authToken]));

  const qrValue = wallet ? `ubanku-demo://pay?code=${wallet.wallet_code}` : '';
  const shareCode = async () => {
    if (!wallet) return;
    await Share.share({
      message: `${wallet.display_name || user?.full_name || 'Demo user'} · Demo wallet code: ${wallet.wallet_code}\n${qrValue}\nDemo transfers only; no real money is sent.`,
    });
  };

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={() => navigation.goBack()}>
      <VStack space={5} px={4} py={6} alignItems="center">
        <UText title center>Receive demo funds</UText>
        <Text style={{textAlign: 'center', color: '#52676A'}}>
          Let another signed-in demo user scan this QR to send simulated funds to your demo wallet.
        </Text>
        {loading ? <Text>Loading your QR…</Text> : null}
        {error ? <Text style={{color: '#B42318', textAlign: 'center'}}>{error}</Text> : null}
        {wallet ? (
          <VStack space={4} alignItems="center" style={{backgroundColor: 'white', padding: 24, borderRadius: 20}}>
            <QRCode value={qrValue} size={220} />
            <Text style={{fontWeight: '700', fontSize: 18}}>{wallet.wallet_code}</Text>
            <Text>{wallet.display_name || user?.full_name || 'Demo user'}</Text>
            <Button title="Share wallet code" onPress={shareCode} />
          </VStack>
        ) : null}
        <Text style={{textAlign: 'center', color: '#7A8A8D', fontSize: 12}}>
          Demo only. This QR cannot receive a real bank, UPI, or payment-provider transfer.
        </Text>
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default ReceiveDemoMoneyPage;
