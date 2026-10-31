import React, {useState} from 'react';
import {Box, Input, FormControl} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import UPinInputs from '../../components/molecules/UPinInputs';
import {RootStackParamList} from '../../navigation/AuthNavigator';

type ForgotPinVerificationProps = {
  route: RouteProp<RootStackParamList, 'ForgotPinVerification'>;
};

const ForgotPinVerification = ({route}: ForgotPinVerificationProps) => {
  const navigation = useNavigation<any>();
  const [pin, setPin] = useState('');
  const {phoneNumber} = route.params;

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleValidationPress = async () => {
    navigation.navigate(
      'ChangePinPage' as never,
      {phoneNumber, verificationCode: pin} as never,
    );
  };

  return (
    <UTitleSubtitleWrapper
      title="Reset your PIN"
      subtitle="We sent a verification code to your mobile number, enter it here"
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      buttonTitle="Continue"
      onPressButton={handleValidationPress}
      isDisabled={pin.length < 5}>
      <Box>
        <FormControl.Label color={'text.500'}>
          Mobile Number
        </FormControl.Label>
        <Input
          keyboardType="phone-pad"
          placeholder="Enter your mobile number"
          value={phoneNumber.cellphone}
          isDisabled
        />
      </Box>

      <UPinInputs
        value={pin}
        setValue={setPin}
        onHandleSubmit={handleValidationPress}
      />
    </UTitleSubtitleWrapper>
  );
};

export default ForgotPinVerification;
