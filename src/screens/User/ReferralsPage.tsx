import {useNavigation} from '@react-navigation/native';
import React from 'react';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UText from '../../components/atoms/UText';
import {
  Box,
  Button,
  HStack,
  Icon,
  Image,
  VStack,
} from 'native-base';
import {MaterialCommunityIcons} from '@expo/vector-icons';
import ReferredCircles from '../../components/organisms/user/referred/ReferredCircles';
import iReferredTransaction from '../../interfaces/Wallet/iReferredTransaction';
import UPressableReferredTransaction from '../../components/molecules/user/referred/UPressableReferredTransaction';
import UBackgroundCard from '../../components/atoms/UBackgroundCard';
import USpacedTexts from '../../components/atoms/USpacedTexts';
import {useLanguage} from '../../contexts/LanguageContext';
import {formatRupees} from '../../utils/currency';

const ReferralsPage = () => {
  const navigation = useNavigation();
  const {t} = useLanguage();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const transactions: iReferredTransaction[] = [
    {
      transactionType: 'Reward',
      transactionName: 'Mariana Castillo',
      transactionDate: '2023-04-04T00:00:00.000Z',
      transactionStatus: 'Approved',
      transactionId: '1356594',
      transactionPaymentMethod: 'UPI',
      transactionValue: 2000,
      referredIcon: require('../../assets/icons/referredGirlIcon.png'),
    },
    {
      transactionType: 'Cashback',
      transactionName: 'Mario Castle',
      transactionDate: '2023-03-18T16:50:00.000Z',
      transactionStatus: 'Approved',
      transactionId: '1356594',
      transactionPaymentMethod: 'Debit Card',
      transactionValue: 8000,
      referredIcon: require('../../assets/icons/referredBoyIcon.png'),
    },
  ];

  const sortedTransactions = [...transactions].sort(
    (a, b) =>
      new Date(b.transactionDate).getTime() -
      new Date(a.transactionDate).getTime(),
  );

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={handleBackPress}>
      <HStack justifyContent={'space-between'} alignItems={'center'}>
        <UText title my={3}>
          {t('referrals')}
        </UText>
        <Button
          height={10}
          leftIcon={
            <Icon
              as={MaterialCommunityIcons}
              name="qrcode-scan"
              color="text.900"
            />
          }
          rounded={40}
          size={'xs'}
          variant={'outline'}
          _text={{fontSize: 12, fontWeight: 400}}>
          ADF45G
        </Button>
      </HStack>
      <HStack marginLeft={'12%'}>
        <ReferredCircles
          circles={[
            {
              name: 'Juan',
              image: require('../../assets/icons/referredBoyIconMd.png'),
            },
            {
              name: 'Mariana',
              image: require('../../assets/icons/referredGirlIconMd.png'),
            },
          ]}
        />
      </HStack>

      <VStack space={5} mt={270}>
        {sortedTransactions.map((transaction, index) => (
          <React.Fragment key={index}>
            <UPressableReferredTransaction
              transaction={transaction}
              onPress={() => {}}
            />
          </React.Fragment>
        ))}
      </VStack>

      <HStack space={2} my={5}>
        <Box flex={0.5}>
          <UBackgroundCard bgColor="tertiary.500" size="sm">
            <HStack flex={1} alignItems={'center'}>
              <VStack flex={0.7}>
                <UText weight={400} text color="text.800" size={10}>
                  {t('friendsInNetwork')}
                </UText>
                <USpacedTexts
                  colorLeft="text.900"
                  fzLeft={16}
                  weightLeft={700}
                  textLeft="2"
                />
              </VStack>
            </HStack>
            <Box position={'absolute'} right={0} bottom={0} mb={-1}>
              <Image
                source={require('../../assets/icons/shakeHandsMd.png')}
                alt="shakeHandsIcon"
              />
            </Box>
          </UBackgroundCard>
        </Box>
        <Box flex={0.5}>
          <UBackgroundCard bgColor="yellow.600" size="sm">
            <HStack flex={1} alignItems={'center'}>
              <VStack flex={0.7}>
                <UText weight={400} text color="text.800" size={10}>
                  {t('referralRewards')}
                </UText>
                <USpacedTexts
                  colorLeft="text.900"
                  fzLeft={16}
                  weightLeft={700}
                  textLeft={`₹ ${formatRupees(5200)}`}
                  colorRight="text.900"
                  fzRight={14}
                  weightRight={700}
                />
              </VStack>
            </HStack>
            <Box position={'absolute'} right={0} bottom={0} mb={-1}>
              <Image
                source={require('../../assets/icons/ucoinMd.png')}
                alt="coinImage"
              />
            </Box>
          </UBackgroundCard>
        </Box>
      </HStack>
      <UBackgroundCard bgColor="info.600" size="sm">
        <HStack flex={1} alignItems={'center'}>
          <VStack flex={0.3}></VStack>

          <VStack flex={0.7} alignItems={'flex-end'}>
            <UText weight={700} size={16} color="text.900">
              {t('receiveReward')}
            </UText>
            <UText weight={400} size={10} color="text.800">
              {t('inviteRewardText')}
            </UText>
            <Button variant={'subtle'} size={'xs'} mt={3}>
              {t('referAFriend')}
            </Button>
          </VStack>
        </HStack>
        <Box position={'absolute'} left={0} bottom={0} mb={-1}>
          <Image
            source={require('../../assets/icons/lipsTalkingMd.png')}
            alt="lips talking"
          />
        </Box>
      </UBackgroundCard>
    </UBasicScrollableNavigationWrapper>
  );
};

export default ReferralsPage;
