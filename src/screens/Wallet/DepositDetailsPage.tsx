import React from 'react';
import UBubblePageNavigationAndOneButton from '../../components/molecules/UBubblePageNavigationAndOneButton';
import TitleAndSubtitle from '../../components/atoms/TitleAndSubtitle';
import {useNavigation} from '@react-navigation/native';
import {Box, Divider, HStack, VStack} from 'native-base';
import UBasicCard from '../../components/atoms/UBasicCard';
import USpacedTexts from '../../components/atoms/USpacedTexts';
import UText from '../../components/atoms/UText';
import {useLanguage} from '../../contexts/LanguageContext';
import {formatRupees} from '../../utils/currency';
import {RouteProp, useRoute} from '@react-navigation/native';

const DepositDetailsPage = () => {
  const navigation = useNavigation<any>();
  const {t} = useLanguage();
  const route = useRoute<RouteProp<any, string>>();
  const depositAmount = Number(route.params?.amount || 0);

  const handleClosePress = () => {
    navigation.goBack();
  };
  const handleBackPress = () => {
    navigation.goBack();
  };
  const handleContinuePress = () => {
    navigation.navigate(
      'DepositConfirmPage' as never,
      {amount: depositAmount, operationId: route.params?.operationId} as never,
    );
  };

  return (
    <UBubblePageNavigationAndOneButton
      bubbleColor="tertiary.100"
      topComponent={
        <Box marginY={10}>
          <TitleAndSubtitle
            title="Review Stripe test checkout"
            subtitle="This checkout only creates a separate Stripe test credit. It does not add demo transfer funds."
          />
        </Box>
      }
      downComponent={
        <Box mt={5} justifyContent={'space-between'} flex={1}>
          <UBasicCard>
            <UText weight={500} size={14} color="text.700">
              {t('depositSummary')}
            </UText>
            <VStack mt={5} space={3.5}>
              <USpacedTexts
                textLeft={t('depositAmount')}
                colorLeft="text.700"
                textRight={`₹ ${formatRupees(depositAmount)}`}
                colorRight="ubanku.2"
                weightLeft={500}
                weightRight={600}
              />
              <USpacedTexts
                textLeft="Test ledger credit"
                colorLeft="text.700"
                textRight={`₹ ${formatRupees(depositAmount)}`}
                colorRight="ubanku.2"
                weightLeft={500}
                weightRight={600}
              />
              <USpacedTexts
                textLeft="Payment fees"
                colorLeft="text.700"
                textRight="Shown in Stripe Checkout"
                colorRight="text.700"
                weightLeft={500}
              />
            </VStack>

            <Divider my={5} />
            <UText weight={500} size={14} color="text.600">
              {t('paymentMethod')}
            </UText>
            <HStack mt={3}>
              <UText weight={600}>Stripe test checkout</UText>
            </HStack>
          </UBasicCard>
          <Box justifyItems={'flex-end'} mt={4}>
            <USpacedTexts
              textLeft={t('totalAmount')}
              fzLeft={16}
              colorLeft="text.700"
              textRight={`₹ ${formatRupees(depositAmount)}`}
              fzRight={20}
              colorRight="ubanku.2"
              weightLeft={600}
              weightRight={700}
            />
          </Box>
        </Box>
      }
              buttonTitle="Continue to Stripe Checkout"
      onPressCloseButton={handleClosePress}
      onPressBackButton={handleBackPress}
      onPressButton={handleContinuePress}
    />
  );
};

export default DepositDetailsPage;
