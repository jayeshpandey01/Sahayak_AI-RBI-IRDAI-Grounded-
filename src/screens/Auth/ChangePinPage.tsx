import React, {useState} from 'react';
import {FormControl, WarningOutlineIcon} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import UPinInputs from '../../components/molecules/UPinInputs';
import {RootStackParamList} from '../../navigation/AuthNavigator';

type ChangePinPageProps = {
  route: RouteProp<RootStackParamList, 'ChangePinPage'>;
};

const ChangePinPage = ({route}: ChangePinPageProps) => {
  const navigation = useNavigation<any>();
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  const {phoneNumber, verificationCode} = route.params;
  const {changePassword} = useAuth();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleCreatePinPress = async () => {
    if (pin.length === 4) {
      let response;
      try { response = await changePassword({
        ...phoneNumber,
        type: 'sms',
        code: verificationCode,
        new_pin: pin,
      }); } catch { setError('Unable to update your PIN. Please try again.'); return; }
      if (response && response.password_changed) {
        navigation.navigate(
          'EnterCustomPin' as never,
          {phoneNumber, trustInDevice: false} as never,
        );
      } else {
        setError(
          'Incorrect verification code. Please try again.',
        );
      }
    }
  };

  return (
    <UTitleSubtitleWrapper
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      title="Create New PIN"
      subtitle="Enter your new security PIN to recover your Ubanku account"
      onPressButton={handleCreatePinPress}
      isDisabled={pin.length < 4}
      buttonTitle="Confirm">
      <FormControl isInvalid={error !== null}>
        <UPinInputs
          setError={error != null}
          size={4}
          value={pin}
          setValue={setPin}
          onHandleSubmit={handleCreatePinPress}
        />
        <FormControl.ErrorMessage leftIcon={<WarningOutlineIcon size="xs" />}>
          {error}
        </FormControl.ErrorMessage>
      </FormControl>
    </UTitleSubtitleWrapper>
  );
};

export default ChangePinPage;
