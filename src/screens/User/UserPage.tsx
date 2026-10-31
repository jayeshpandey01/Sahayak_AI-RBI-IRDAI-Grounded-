import React from 'react';
import UBubblePageNavigationAndOneButton from '../../components/molecules/UBubblePageNavigationAndOneButton';
import {useNavigation} from '@react-navigation/native';
import {
  Box,
  Divider,
  HStack,
  Image,
  Text,
  VStack,
} from 'native-base';
import UText from '../../components/atoms/UText';
import UuserMenuPressable from '../../components/molecules/user/UuserMenuPressable';
import {useLanguage} from '../../contexts/LanguageContext';
import {useAuth} from '../../contexts/AuthContext';

const UserPage = () => {
  const navigation = useNavigation();
  const {user, logout} = useAuth();
  const {t, currentLanguage, languages} = useLanguage();

  const currentLangObj = languages.find(l => l.code === currentLanguage) || languages[0];

  const handleBackPress = () => {
    navigation.goBack();
  };

  return (
    <UBubblePageNavigationAndOneButton
      bubbleColor="yellow.300"
      topComponent={
        <Box>
          <HStack alignItems={'center'} space={3} mt={2}>
            <Image
              alt="user default icon"
              source={require('../../assets/icons/userIcon.png')}
            />
            <VStack>
              <UText size={20} weight={500} color="ubanku.2">
                {user?.full_name || t('user')}
              </UText>
              {user?.email ? (
                <Text fontSize="xs" color="text.600" fontWeight={400}>
                  {user.email}
                </Text>
              ) : null}
            </VStack>
          </HStack>
        </Box>
      }
      downComponent={
        <>
          <VStack my={5} space={4}>
            <UuserMenuPressable
              icon="user"
              text={t('profileDetails')}
              onPress={() => navigation.navigate('ProfileDetailsPage' as never)}
            />
            <UuserMenuPressable
              icon="user-plus"
              text={t('referrals')}
              onPress={() => navigation.navigate('ReferralsPage' as never)}
            />
            <UuserMenuPressable
              icon="credit-card"
              text={t('paymentMethods')}
              onPress={() => undefined}
            />
            <UuserMenuPressable
              icon="shopping-bag"
              text={t('yourOrders')}
              onPress={() => undefined}
            />
            <Divider />
            <UText weight={500} size={11} color="text.500">
              {t('settings')}
            </UText>
            <UuserMenuPressable
              icon="globe"
              text={`${t('language')} (${currentLangObj.nativeLabel})`}
              onPress={() => navigation.navigate('LanguageSettingsPage' as never)}
            />
            <Divider />
            <UText weight={500} size={11} color="text.500">
              {t('help')}
            </UText>
            <UuserMenuPressable
              icon="life-buoy"
              text={t('support')}
              onPress={() => undefined}
            />
            <UuserMenuPressable
              icon="help-circle"
              text={t('faqs')}
              onPress={() => undefined}
            />
            <Divider />
            <UuserMenuPressable
              icon="log-out"
              text={t('signOut')}
              onPress={() => logout()}
            />
          </VStack>
        </>
      }
      onPressBackButton={handleBackPress}
    />
  );
};

export default UserPage;
