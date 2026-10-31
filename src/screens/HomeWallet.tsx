import React, {useState} from 'react';
import {
  Box,
  Button,
  Divider,
  HStack,
  Icon,
  IconButton,
  Image,
  VStack,
} from 'native-base';
import {
  MaterialCommunityIcons,
  Octicons,
  Entypo,
  Feather,
} from '@expo/vector-icons';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import {
  getDemoWallet,
  getDemoWalletEntries,
} from '../services/sahayakApi';
import UBasicScrollableWrapper from '../components/molecules/UBasicScrollableWrapper';
import UText from '../components/atoms/UText';
import UBackgroundCard from '../components/atoms/UBackgroundCard';
import USpacedTexts from '../components/atoms/USpacedTexts';
import UPressableTransaction from '../components/molecules/wallet/UPressableTransaction';
import iTransaction from '../interfaces/Wallet/iTransaction';
import iWithdrawal from '../interfaces/Wallet/iWithdrawal';
import UModalTransactionWithInfo from '../components/molecules/wallet/UModalTransactionWithInfo';
import {useLanguage} from '../contexts/LanguageContext';
import {formatRupees} from '../utils/currency';
import {useAuth} from '../contexts/AuthContext';
import {apiErrorMessage} from '../services/apiClient';

const HomeWallet = () => {
  const navigation = useNavigation();
  const {t} = useLanguage();
  const {authToken} = useAuth();

  const [modalVisible, setModalVisible] = useState(false);
  const [walletBalance, setWalletBalance] = useState(0);
  const [walletLoading, setWalletLoading] = useState(true);
  const [walletError, setWalletError] = useState('');
  const [localTransactions, setLocalTransactions] = useState<any[]>([]);
  const loadWallet = React.useCallback(async (isActive: () => boolean = () => true) => {
    if (!authToken) {
      setWalletBalance(0);
      setLocalTransactions([]);
      setWalletError('Sign in to load your demo wallet.');
      setWalletLoading(false);
      return;
    }
    setWalletLoading(true);
    setWalletError('');
    const [demoWallet, entries] = await Promise.allSettled([
      getDemoWallet(authToken), getDemoWalletEntries(authToken),
    ]);
    if (!isActive()) return;
    if (demoWallet.status === 'fulfilled') {
      setWalletBalance(demoWallet.value.balance_paise / 100);
    } else {
      setWalletError(apiErrorMessage(demoWallet.reason));
    }
    if (entries.status === 'fulfilled') {
      setLocalTransactions(entries.value.map(entry => ({
        transactionType: entry.entry_type === 'DEBIT' ? 'Send' : 'Deposit',
        transactionName: entry.description,
        transactionDate: entry.created_at,
        transactionStatus: 'SIMULATED',
        transactionId: entry.transaction_id,
        transactionPaymentMethod: 'DEMO WALLET',
        transactionValue: entry.amount_paise / 100,
      })));
    } else if (demoWallet.status === 'fulfilled') {
      setWalletError(apiErrorMessage(entries.reason));
    }
    setWalletLoading(false);
  }, [authToken]);
  useFocusEffect(
    React.useCallback(() => {
      let active = true;
      void loadWallet(() => active);
      return () => {
        active = false;
      };
    }, [loadWallet]),
  );
  const [selectedTransaction, setSelectedTransaction] = useState<
    iTransaction | iWithdrawal | null
  >(null);

  const handlePress = (transaction: iTransaction | iWithdrawal) => {
    setSelectedTransaction(transaction);
    setModalVisible(true);
  };

  const sortedTransactions = [...localTransactions].sort(
    (a, b) =>
      new Date(b.transactionDate).getTime() -
      new Date(a.transactionDate).getTime(),
  );

  return (
    <UBasicScrollableWrapper>
      <HStack justifyContent={'space-between'} alignItems={'center'} mb={5}>
        <UText size={20} weight={400} color="text.900">
          {t('wallet')}
        </UText>
        <Button
          leftIcon={<Icon as={Octicons} name="gift" color="text.900" />}
          rounded={40}
          variant={'outline'}
          onPress={() => navigation.navigate('UserMenu' as never)}
          _text={{fontSize: 12, fontWeight: 400}}>
          {t('referAFriend')}
        </Button>
      </HStack>
      <UBackgroundCard bgColor="secondary.600">
        <HStack my={5}>
          <VStack flex={0.7}>
            <UText text color="text.50">
            Demo wallet balance
            </UText>
            <UText title color="text.50" weight={700}>
              {walletLoading ? 'Loading…' : walletError ? 'Unavailable' : `₹ ${formatRupees(walletBalance)}`}
            </UText>
            <UText text color="text.50" size={10}>
              Temporary demo funds only. QR sends debit this balance and credit another demo user. No real money moves.
            </UText>
            <HStack justifyContent="space-between" mt={6} mb={1}>
              <VStack alignItems="center">
                <IconButton
                  variant="ghost"
                  rounded="full"
                  size={'lg'}
                  bg="#335459"
                  _web={{cursor: 'pointer'}}
                  _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                  _pressed={{transform: [{scale: 0.95}]}}
                  icon={
                    <Icon
                      as={Feather}
                      name="plus-circle"
                      color="text.50"
                    />
                  }
                  onPress={() => navigation.navigate('FundDemoWallet' as never)}
                />
                <UText text weight={400} size={12} color="text.50">
                  Add demo funds
                </UText>
              </VStack>
              <VStack alignItems="center">
                <IconButton
                  variant="ghost"
                  rounded="full"
                  size={'lg'}
                  bg="#335459"
                  _web={{cursor: 'pointer'}}
                  _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                  _pressed={{transform: [{scale: 0.95}]}}
                  icon={<Icon as={MaterialCommunityIcons} name="send" color="text.50" />}
                  onPress={() => navigation.navigate('Send' as never)}
                />
                <UText text weight={400} size={12} color="text.50">
                  Send demo
                </UText>
              </VStack>
              <VStack alignItems="center">
                <IconButton
                  variant="ghost"
                  rounded="full"
                  size={'lg'}
                  bg="#335459"
                  _web={{cursor: 'pointer'}}
                  _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                  _pressed={{transform: [{scale: 0.95}]}}
                  icon={<Icon as={MaterialCommunityIcons} name="qrcode" color="text.50" />}
                  onPress={() => navigation.navigate('ReceiveDemoMoney' as never)}
                />
                <UText text weight={400} size={12} color="text.50">
                  Receive QR
                </UText>
              </VStack>
            </HStack>
          </VStack>
          <VStack flex={0.3}></VStack>
        </HStack>
        <Box position={'absolute'} right={0} bottom={0} mb={-1}>
          <Image
            source={require('../assets/icons/PodiumCoin1.png')}
            alt="podiumCoinImage"
          />
        </Box>
      </UBackgroundCard>
      {walletError ? <VStack space={2}>
        <UText text color="error.600" size={12}>{walletError}</UText>
        <Button size="sm" variant="outline" onPress={() => void loadWallet()}>Retry wallet connection</Button>
      </VStack> : null}
      <HStack space={2} my={5}>
        <Box flex={0.5}>
          <UBackgroundCard bgColor="yellow.300">
            <HStack flex={1}>
              <VStack flex={0.7}>
                <UText weight={400} text color="text.800" size={10}>
                  {t('totalCashbackReceived')}
                </UText>
                <USpacedTexts
                  colorLeft="text.900"
                  fzLeft={16}
                  weightLeft={700}
                  textLeft="Demo only"
                  colorRight="text.900"
                  fzRight={14}
                  weightRight={700}
                />
              </VStack>
              <VStack flex={0.3}></VStack>
            </HStack>
            <Box position={'absolute'} right={0} bottom={0} mb={-1}>
              <Image
                source={require('../assets/icons/ReturnCoin.png')}
                alt="podiumCoinImage"
              />
            </Box>
          </UBackgroundCard>
        </Box>
        <Box flex={0.5}>
          <UBackgroundCard bgColor="tertiary.600">
            <HStack flex={1}>
              <VStack flex={0.7}>
                <UText weight={400} text color="text.800" size={10}>
                  {t('referralRewards')}
                </UText>
                <USpacedTexts
                  colorLeft="text.900"
                  fzLeft={16}
                  weightLeft={700}
                  textLeft="Demo only"
                  colorRight="text.900"
                  fzRight={14}
                  weightRight={700}
                />
              </VStack>
              <VStack flex={0.3}></VStack>
            </HStack>
            <Box position={'absolute'} right={0} bottom={0} mb={-1}>
              <Image
                source={require('../assets/icons/users.png')}
                alt="podiumCoinImage"
              />
            </Box>
          </UBackgroundCard>
        </Box>
      </HStack>
      <Box mt={2}>
        <UText size={16} subtitle color="text.900">
          {t('transactions')}
        </UText>
        <VStack space={5} mt={5}>
          {sortedTransactions.map((transaction, index) => (
            <React.Fragment key={index}>
              <UPressableTransaction
                transaction={transaction}
                onPress={() => handlePress(transaction)}
              />
              {index < sortedTransactions.length - 1 &&
                new Date(
                  sortedTransactions[index].transactionDate,
                ).toDateString() !==
                  new Date(
                    sortedTransactions[index + 1].transactionDate,
                  ).toDateString() && <Divider />}
            </React.Fragment>
          ))}
        </VStack>
        <Button
          alignSelf={'center'}
          variant={'link'}
          rightIcon={<Icon as={Entypo} name="plus" color="primary.600" />}
          _text={{
            color: 'primary.600',
            textAlign: 'center',
            width: '100%',
            fontSize: 12,
            fontWeight: 500,
          }}
          fontSize="sm"
          mt={7}
          onPress={() => navigation.navigate('Wallet' as never)}>
          {t('viewMoreTransactions')}
        </Button>
        {selectedTransaction && (
          <UModalTransactionWithInfo
            visible={modalVisible}
            onClose={() => setModalVisible(false)}
            {...selectedTransaction}
            transactionPaymentMethod={
              selectedTransaction.transactionPaymentMethod || '-'
            }
          />
        )}
      </Box>
    </UBasicScrollableWrapper>
  );
};

export default HomeWallet;
