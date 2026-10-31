import React from 'react';
import {useNavigation} from '@react-navigation/native';
import UTitleSubtitleCenterTwoButtons from '../../components/molecules/UTitleSubtitleCenterTwoButtons';

const TrustInDevice = ({route}: any) => {
  const navigation = useNavigation<any>();
  const {phoneNumber} = route.params;

  const handleTrustDevice = () => {
    navigation.navigate(
      'EnterCustomPin' as never,
      {phoneNumber, trustInDevice: true} as never,
    );
  };

  const handleDontTrust = () => {
    navigation.navigate(
      'EnterCustomPin' as never,
      {phoneNumber, trustInDevice: false} as never,
    );
  };

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  return (
    <UTitleSubtitleCenterTwoButtons
      title="Do you trust this device?"
      subtitle="We won't ask for verification again if you mark this device as trusted. Would you like to add it as a trusted device?"
      onPressBackButton={handleBackPress}
      firstButtonTitle="Yes, trust this device"
      onPressCloseButton={handleClosePress}
      onPressFirstButton={handleTrustDevice}
      onPressSecondButton={handleDontTrust}
      secondButtonTitle="No, skip"
      icon={require('../../assets/icons/shieldIcon.png')}
    />
  );
};

export default TrustInDevice;
