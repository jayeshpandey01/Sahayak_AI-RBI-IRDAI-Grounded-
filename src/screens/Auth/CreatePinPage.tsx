import React, {useState} from 'react';
import {Alert} from 'react-native';
import {RouteProp, useNavigation} from '@react-navigation/native';
import {useAuth} from '../../contexts/AuthContext';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import UPinInputs from '../../components/molecules/UPinInputs';
import {RootStackParamList} from '../../navigation/AuthNavigator';

type CreatePinPageProps = {
  route: RouteProp<RootStackParamList, 'CreatePinPage'>;
};

const CreatePinPage = ({route}: CreatePinPageProps) => {
  const navigation = useNavigation<any>();
  const [pin, setPin] = useState('');
  const {newUserData} = route.params;
  const {register} = useAuth();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleCreatePinPress = async () => {
    if (pin.length === 4) {
      try {
        await register({...newUserData, pin: pin});
      } catch (error) {
        Alert.alert('Registration failed', 'We could not create your account. Check your connection and try again.');
      }
    }
  };

  return (
    <UTitleSubtitleWrapper
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}
      title="Create 4-Digit PIN"
      subtitle="Please create a new 4-digit PIN to secure your account."
      onPressButton={handleCreatePinPress}
      isDisabled={pin.length < 4}
      buttonTitle="Create PIN">
      <UPinInputs
        size={4}
        value={pin}
        setValue={setPin}
        onHandleSubmit={handleCreatePinPress}
      />
    </UTitleSubtitleWrapper>
  );
};

export default CreatePinPage;
