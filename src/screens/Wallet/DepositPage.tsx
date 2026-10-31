import React, {useEffect, useState} from 'react';
import UBubblePageNavigationAndOneButton from '../../components/molecules/UBubblePageNavigationAndOneButton';
import TitleAndSubtitle from '../../components/atoms/TitleAndSubtitle';
import {useNavigation} from '@react-navigation/native';
import {Box, HStack, Text, VStack, WarningIcon} from 'native-base';
import UBasicCard from '../../components/atoms/UBasicCard';
import USpacedTexts from '../../components/atoms/USpacedTexts';
import ULine from '../../components/atoms/ULine';
import UCashInput from '../../components/atoms/UCashInput';
import UText from '../../components/atoms/UText';
import {useLanguage} from '../../contexts/LanguageContext';
import {formatRupees} from '../../utils/currency';
import {getServerWalletBalance} from '../../services/sahayakApi';
import {useAuth} from '../../contexts/AuthContext';

const DepositPage = () => {
  const navigation = useNavigation<any>();
  const {t} = useLanguage();
  const {authToken} = useAuth();
  const [available, setAvailable] = useState(0);
  const [valueError, setValueError] = useState<string>('');
  const [value, setValue] = useState<number>(0);
  useEffect(() => {
    if (authToken)
      getServerWalletBalance(authToken)
        .then(wallet => setAvailable(wallet.balance_paise / 100))
        .catch(() => setAvailable(0));
    else setAvailable(0);
  }, [authToken]);

  const handleClosePress = () => {
    navigation.goBack();
  };
  const handleContinuePress = () => {
    if (value <= 0) {
      setValueError('Please enter an amount to deposit');
      return;
    }
    navigation.navigate(
      'DepositDetailsPage' as never,
      {amount: value, operationId: `wallet-topup-${Date.now()}`} as never,
    );
  };

  return (
    <UBubblePageNavigationAndOneButton
      bubbleColor="tertiary.100"
      topComponent={
        <Box marginY={10}>
          <TitleAndSubtitle
            title="Stripe test checkout"
            subtitle="Create separate Stripe test credits for checkout testing. These credits are not added to the simulated demo wallet and cannot be sent or withdrawn."
          />
        </Box>
      }
      downComponent={
        <Box my={5}>
          <UBasicCard>
            <USpacedTexts
              textLeft="Separate Stripe test credits"
              colorLeft="text.600"
              textRight={`₹ ${formatRupees(available)}`}
              colorRight="text.900"
              weightRight={600}
            />
            <Box flexDirection="row" mt={5}>
              <UText subtitle>Test checkout amount</UText>
            </Box>

            <HStack width={'100%'} alignItems={'center'} mb={5}>
              <Box flex={0.7}>
                <UCashInput sign="₹ " value={value} setValue={setValue} />
              </Box>
              <Box
                flex={0.3}
                flexDir="row"
                justifyContent={'center'}
                alignItems={'center'}>
                <Box
                  bg="primary.600"
                  px={3}
                  py={1}
                  rounded="full"
                  alignItems="center"
                  justifyContent="center">
                  <Text color="white" fontWeight={700} fontSize={14}>
                    ₹ INR
                  </Text>
                </Box>
              </Box>
            </HStack>
            <ULine />

            <VStack mt={5} space={5}>
              <UText subtitle>
                Complete the test payment in Stripe Checkout. This does not add simulated demo funds.
              </UText>
            </VStack>

            {valueError ? (
              <HStack alignItems={'center'} mt={3}>
                <WarningIcon size="xs" color={'error.600'} mr={2} />
                <Text fontWeight={400} fontSize={13} color={'error.600'}>
                  {valueError}
                </Text>
              </HStack>
            ) : null}
          </UBasicCard>
        </Box>
      }
      buttonTitle={t('continue')}
      onPressCloseButton={handleClosePress}
      onPressButton={handleContinuePress}
    />
  );
};

export default DepositPage;
