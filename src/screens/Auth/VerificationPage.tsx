import React, {useState} from 'react';
import {Box, Input, FormControl, Link} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import UPinInputs from '../../components/molecules/UPinInputs';
import Countdown from '../../components/organisms/Countdown';
import {RootStackParamList} from '../../navigation/AuthNavigator';

type VerificationPageProps = {
  route: RouteProp<RootStackParamList, 'VerificationPage'>;
};

const VerificationPage = ({route}: VerificationPageProps) => {
  const navigation = useNavigation<any>();
  const [pin, setPin] = useState('');
  const [error, setError] = useState<boolean>(false);
  const {phoneNumber, newUser} = route.params;
  const {checkVerificationCode, sendVerificationCode} = useAuth();

  const handleNewCodeRequest = async () => {
    let response;
    try { response = await sendVerificationCode(phoneNumber); } catch { setError(true); return false; }
    if (
      response &&
      response.sent &&
      response.cellphone === phoneNumber.phone_code + phoneNumber.cellphone
    ) {
      return true;
    } else {
      return false;
    }
  };

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleValidationPress = async () => {
    let response;
    try { response = await checkVerificationCode({...phoneNumber, code: pin}); } catch { setError(true); return; }
    if (response && response.valid) {
      if (newUser) {
        navigation.navigate(
          'RegistrationPage' as never,
          {phoneNumber} as never,
        );
      } else {
        navigation.navigate('TrustInDevice' as never, {phoneNumber} as never);
      }
    } else setError(true);
  };

  return (
    <UTitleSubtitleWrapper
      title="Verification"
      subtitle="We sent a verification code to your phone. Enter it here"
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      buttonTitle="Verify"
      onPressButton={handleValidationPress}
      isDisabled={pin.length < 5}
      additionalComponent={
        <Countdown initialCount={60} onEndCount={handleNewCodeRequest} />
      }>
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
        setError={error}
        size={5}
        value={pin}
        setValue={setPin}
        onHandleSubmit={handleValidationPress}
      />

      <Link
        _text={{
          color: 'primary.600',
          textAlign: 'center',
          width: '100%',
        }}
        fontSize="sm"
        mt={4}
        position="absolute"
        bottom={5}
        onPress={null}>
        Need help?
      </Link>
    </UTitleSubtitleWrapper>
  );
};

export default VerificationPage;
