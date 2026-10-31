import React, {useState} from 'react';
import {Text, FormControl, WarningOutlineIcon, Link} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import UPinInputs from '../../components/molecules/UPinInputs';
import {RootStackParamList} from '../../navigation/AuthNavigator';
import iRegisterPhoneData from '../../interfaces/Auth/iRegisterPhoneData';

type EnterCustomPinProps = {
  route: RouteProp<RootStackParamList, 'EnterCustomPin'>;
};

const EnterCustomPin = ({route}: EnterCustomPinProps) => {
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation<any>();
  const [pin, setPin] = useState('');
  const {phoneNumber, trustInDevice} = route.params;

  const {login, loginError, sendVerificationCode} = useAuth();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleForgotPinPress = async () => {
    const user: iRegisterPhoneData = {...phoneNumber, type: 'sms'};
    const response = await sendVerificationCode(user);
    if (
      response &&
      response.sent &&
      response.cellphone === phoneNumber.phone_code + phoneNumber.cellphone
    ) {
      navigation.navigate(
        'ForgotPinVerification' as never,
        {
          phoneNumber: user,
        } as never,
      );
    }
  };

  const handleValidationPress = async () => {
    setError(null);
    try {
      await login({...phoneNumber, pin}, trustInDevice);
    } catch (e: any) {
      setError(e?.message || loginError || 'Unable to sign in. Check your details and try again.');
    }
  };

  return (
    <UTitleSubtitleWrapper
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      title="Enter your PIN"
      subtitle="Enter your security PIN to access your Ubanku account"
      buttonTitle="Confirm"
      onPressButton={handleValidationPress}
      isDisabled={pin.length !== 4}>
      <FormControl isInvalid={error !== null}>
        <UPinInputs
          setError={error != null}
          isPassword
          size={4}
          value={pin}
          setValue={setPin}
          onHandleSubmit={handleValidationPress}
        />
        <FormControl.ErrorMessage leftIcon={<WarningOutlineIcon size="xs" />}>
          {error}
        </FormControl.ErrorMessage>
      </FormControl>
      <Text
        fontSize="sm"
        textAlign="center"
        mt={4}
        position="absolute"
        bottom={5}
        right={0}
        left={0}>
        Forgot your PIN?{' '}
        <Link _text={{color: 'primary.800'}} onPress={handleForgotPinPress}>
          Reset it here
        </Link>
      </Text>
    </UTitleSubtitleWrapper>
  );
};

export default EnterCustomPin;
