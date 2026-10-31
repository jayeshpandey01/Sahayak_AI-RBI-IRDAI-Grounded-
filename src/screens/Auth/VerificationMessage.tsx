import React from 'react';
import {Box, Button, HStack, FormControl, Input, Text, Icon} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import {FontAwesome} from '@expo/vector-icons';
import {RootStackParamList} from '../../navigation/AuthNavigator';
import {useAuth} from '../../contexts/AuthContext';
import iRegisterPhoneData from '../../interfaces/Auth/iRegisterPhoneData';
import {Alert} from 'react-native';

type VerificationMessageProps = {
  route: RouteProp<RootStackParamList, 'VerificationMessage'>;
};

const VerificationMessage = ({route}: VerificationMessageProps) => {
  const navigation = useNavigation<any>();
  const {phoneNumber, newUser} = route.params;
  const {sendVerificationCode} = useAuth();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleSMSVerificationPress = async () => {
    const user: iRegisterPhoneData = {...phoneNumber, type: 'sms'};
    let response;
    try { response = await sendVerificationCode(user); } catch { Alert.alert('Code not sent', 'The verification service could not send a code. Please try again.'); return; }
    if (
      response &&
      response.sent &&
      response.cellphone === phoneNumber.phone_code + phoneNumber.cellphone
    ) {
      navigation.navigate(
        'VerificationPage' as never,
        {
          phoneNumber: user,
          newUser,
        } as never,
      );
    }
  };

  const handleWhatsAppVerificationPress = async () => {
    const user: iRegisterPhoneData = {...phoneNumber, type: 'wsp'};
    let response;
    try { response = await sendVerificationCode(user); } catch { Alert.alert('Code not sent', 'The verification service could not send a code. Please try again.'); return; }
    if (response && response.sent) {
      navigation.navigate(
        'VerificationPage' as never,
        {phoneNumber: user, newUser} as never,
      );
    }
  };

  return (
    <UTitleSubtitleWrapper
      title="Verification"
      subtitle="We will send a verification code to your mobile number. Choose where you want to receive it."
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}>
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
      <HStack space={2} justifyContent="space-between" mt={4}>
        <Button
          onPress={handleWhatsAppVerificationPress}
          width="48%"
          leftIcon={
            <Icon
              as={FontAwesome}
              name="whatsapp"
              color="secondary.500"
              size={'sm'}
            />
          }>
          <Text color={'text.900'} fontWeight={'500'}>
            WhatsApp
          </Text>
        </Button>
        <Button
          onPress={handleSMSVerificationPress}
          width="48%"
          variant="subtle"
          leftIcon={
            <Icon
              as={FontAwesome}
              name="comment-o"
              color="neutral.0"
              size={'sm'}
            />
          }>
          <Text color={'neutral.0'} fontWeight={'500'}>
            SMS
          </Text>
        </Button>
      </HStack>
    </UTitleSubtitleWrapper>
  );
};

export default VerificationMessage;
