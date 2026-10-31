import React from 'react';
import {useNavigation} from '@react-navigation/native';
import UTitleSubtitleBasicTwoButtons from '../../components/molecules/UTitleSubtitleBasicTwoButtons';

const ReferralWelcome = () => {
  const navigation = useNavigation();

  const handleReferralWelcome = async () => {
    navigation.navigate('AuthenticationPage' as never);
  };

  const handleCancel = () => {
    navigation.navigate('HelloScreen' as never);
  };

  return (
    <UTitleSubtitleBasicTwoButtons
      title="Andy invited you to Ubanku!"
      subtitle="You've been invited to Ubanku to start achieving your financial goals, and we have a welcome bonus for you! 🎁"
      firstButtonTitle="Get Started!"
      onPressFirstButton={handleReferralWelcome}
      onPressSecondButton={handleCancel}
      secondButtonTitle="Cancel"
      icon={require('../../assets/icons/congratsHandsIcon.png')}
    />
  );
};

export default ReferralWelcome;
