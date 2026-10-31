import React, {useState} from 'react';
import {Box, Input, FormControl, WarningOutlineIcon} from 'native-base';
import {Alert} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import iRegisterPhoneData from '../../interfaces/Auth/iRegisterPhoneData';

const AuthenticationPage = () => {
  const navigation = useNavigation<any>();
  const [phoneNumber, setPhoneNumber] = useState<iRegisterPhoneData>({
    phone_code: '91',
    cellphone: '',
  });
  const [phoneError, setPhoneError] = useState<string>('');
  const {isRegistered} = useAuth();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleLogin = async () => {
    if (isValidPhone(phoneNumber.cellphone)) {
      setPhoneError('');

      let userInfo;
      try {
        userInfo = await isRegistered(phoneNumber);
      } catch {
        Alert.alert('Cannot connect', 'The authentication service is unavailable. Check your API configuration and try again.');
        return;
      }
      let newUser: boolean = true;
      if (userInfo?.exist_phone) {
        if (userInfo?.trusted_device) {
          navigation.navigate(
            'EnterCustomPin' as never,
            {phoneNumber} as never,
          );
        } else {
          navigation.navigate(
            'VerificationMessage' as never,
            {phoneNumber, newUser: false} as never,
          );
        }
      } else {
        navigation.navigate(
          'VerificationMessage' as never,
          {phoneNumber, newUser} as never,
        );
      }
    } else {
      setPhoneError('Invalid mobile number');
    }
  };

  const isValidPhone = (phone: string) => {
    var re = /^[0-9]{9,}$/;
    return re.test(phone);
  };

  const handlePhoneChange = (text: string) => {
    const cleaned = ('' + text).replace(/\D/g, '');
    setPhoneNumber({...phoneNumber, cellphone: cleaned});
  };

  return (
    <UTitleSubtitleWrapper
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      title="Sign In or Sign Up"
      subtitle="Enter your mobile number to sign in or register with Ubanku"
      buttonTitle="Continue"
      onPressButton={handleLogin}>
      <Box>
        <FormControl isInvalid={phoneError !== ''}>
          <FormControl.Label color={'text.500'}>
            Mobile Number
          </FormControl.Label>
          <Input
            keyboardType="phone-pad"
            placeholder="Enter your mobile number"
            value={phoneNumber.cellphone}
            onChangeText={handlePhoneChange}
          />
          <FormControl.ErrorMessage leftIcon={<WarningOutlineIcon size="xs" />}>
            {phoneError}
          </FormControl.ErrorMessage>
        </FormControl>
      </Box>
    </UTitleSubtitleWrapper>
  );
};

export default AuthenticationPage;
