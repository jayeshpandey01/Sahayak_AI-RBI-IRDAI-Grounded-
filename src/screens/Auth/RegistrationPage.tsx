import React, {useRef, useState} from 'react';
import {
  Box,
  VStack,
  Text,
  Button,
  Input,
  Checkbox,
  Select,
  FormControl,
  WarningOutlineIcon,
} from 'native-base';
import {RouteProp, useNavigation} from '@react-navigation/native';
import UTitleSubtitleWrapper from '../../components/molecules/UTitleSubtitleWrapper';
import {KeyboardAwareScrollView} from 'react-native-keyboard-aware-scroll-view';
import {TextInput} from 'react-native';
import {RootStackParamList} from '../../navigation/AuthNavigator';
import useUserForm from '../../hooks/Auth/useUserForm';
import iRegisterNewUserData from '../../interfaces/Auth/iRegisterNewUserData';

type RegistrationPageProps = {
  route: RouteProp<RootStackParamList, 'RegistrationPage'>;
};

const validateName = (text: string) => (text ? '' : 'Please enter your name');
const validateEmail = (text: string) =>
  /\S+@\S+\.\S+/.test(text) ? '' : 'Please enter a valid email';
const validateDream = (text: string) => (text ? '' : 'Please enter your dream / goal');
const validateUniversity = (text: string) =>
  text ? '' : 'Please select your institution / city';
const validateReferralCode = (text: string) =>
  text === '' || text.length >= 5
    ? ''
    : 'Referral code must have at least 5 characters';

const RegistrationPage = ({route}: RegistrationPageProps) => {
  const navigation = useNavigation<any>();
  const name = useUserForm('', validateName);
  const email = useUserForm('', validateEmail);
  const dream = useUserForm('', validateDream);
  const university = useUserForm('', validateUniversity);
  const referralCode = useUserForm('', validateReferralCode);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const {phoneNumber} = route.params;

  const emailInputRef = useRef<any>(null);
  const dreamInputRef = useRef<any>(null);
  const referralCodeInputRef = useRef<any>(null);

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleClosePress = () => {
    navigation.navigate('HelloScreen' as never);
  };

  const handleCreateAccount = () => {
    const newUser: iRegisterNewUserData = {
      first_name: name.value,
      cellphone: phoneNumber.cellphone,
      phone_code: phoneNumber.phone_code,
      dream_name: dream.value,
      email: email.value,
      university_id: university.value,
      is_student: true,
      pin: '',
    };

    navigation.navigate(
      'CreatePinPage' as never,
      {newUserData: newUser} as never,
    );
  };

  const handleRegisterPress = () => {
    const fields = [name, email, dream, university, referralCode];

    const allValid = fields.every(field => {
      field.validate();
      return field.error === '';
    });

    if (allValid && termsAccepted) {
      handleCreateAccount();
    }
  };

  return (
    <UTitleSubtitleWrapper
      title="Register"
      subtitle="Welcome! Let's get some basic details to complete your profile"
      onPressBackButton={handleBackPress}
      onPressCloseButton={handleClosePress}>
      <KeyboardAwareScrollView
        style={{flex: 1}}
        resetScrollToCoords={{x: 0, y: 0}}
        scrollEnabled={true}>
        <Box style={{flex: 1}}>
          <Box flex={0.85}>
            <VStack space={2} width="100%" flex={1}>
              <FormControl isInvalid={name.error !== ''}>
                <FormControl.Label color={'text.500'}>Full Name</FormControl.Label>
                <Input
                  placeholder="Andy Sharma"
                  value={name.value}
                  onChangeText={name.onChange}
                  onSubmitEditing={() => emailInputRef.current?.focus()}
                  returnKeyType="next"
                />
                <FormControl.ErrorMessage
                  leftIcon={<WarningOutlineIcon size="xs" />}>
                  {name.error}
                </FormControl.ErrorMessage>
              </FormControl>
              <FormControl isInvalid={email.error !== ''}>
                <FormControl.Label color={'text.500'}>Email</FormControl.Label>
                <Input
                  placeholder="andy@example.com"
                  value={email.value}
                  onChangeText={email.onChange}
                  keyboardType="email-address"
                  onSubmitEditing={() => dreamInputRef.current?.focus()}
                  returnKeyType="next"
                  ref={emailInputRef}
                />
                <FormControl.ErrorMessage
                  leftIcon={<WarningOutlineIcon size="xs" />}>
                  {email.error}
                </FormControl.ErrorMessage>
              </FormControl>
              <FormControl isInvalid={dream.error !== ''}>
                <FormControl.Label color={'text.500'}>
                  What is your biggest financial goal / dream?
                </FormControl.Label>
                <Input
                  placeholder="Trip to Goa / Start a business"
                  value={dream.value}
                  onChangeText={dream.onChange}
                  returnKeyType="next"
                  ref={dreamInputRef}
                />
                <FormControl.ErrorMessage
                  leftIcon={<WarningOutlineIcon size="xs" />}>
                  {dream.error}
                </FormControl.ErrorMessage>
              </FormControl>
              <FormControl isInvalid={university.error !== ''}>
                <FormControl.Label color={'text.500'}>
                  Select your institution / city
                </FormControl.Label>
                <Select
                  accessibilityLabel="Choose institution or city"
                  selectedValue={university.value}
                  onValueChange={university.onChange}
                  placeholder="Select one">
                  <Select.Item label="Mumbai University" value="mumbai" />
                  <Select.Item label="Delhi University" value="delhi" />
                  <Select.Item label="Pune University" value="pune" />
                  <Select.Item label="Other" value="other" />
                </Select>
                <FormControl.ErrorMessage
                  leftIcon={<WarningOutlineIcon size="xs" />}>
                  {university.error}
                </FormControl.ErrorMessage>
              </FormControl>

              <FormControl isInvalid={referralCode.error !== ''}>
                <FormControl.Label color={'text.500'}>
                  Referral code (Optional)
                </FormControl.Label>
                <Input
                  placeholder="ADF45G (optional)"
                  value={referralCode.value}
                  onChangeText={referralCode.onChange}
                  ref={referralCodeInputRef}
                />
                <FormControl.ErrorMessage
                  leftIcon={<WarningOutlineIcon size="xs" />}>
                  {referralCode.error}
                </FormControl.ErrorMessage>
                <Text fontSize={12} my={1} color={'text.500'}>
                  Only if applicable
                </Text>
              </FormControl>
            </VStack>
          </Box>

          <Box flex={0.15} mt={4}>
            <VStack space={3} justifyContent={'flex-end'}>
              <Checkbox
                value="terms"
                isChecked={termsAccepted}
                onChange={isChecked => setTermsAccepted(isChecked)}>
                <Text fontSize={12} width={'90%'} color={'text.900'}>
                  I understand and agree to the{' '}
                  <Text color={'primary.800'}>Terms of Service</Text> and{' '}
                  <Text color={'primary.800'}>Privacy Policy</Text>
                </Text>
              </Checkbox>

              <Button
                onPress={handleRegisterPress}
                width="100%"
                mb={2}
                isDisabled={!termsAccepted}>
                Create My Account
              </Button>
            </VStack>
          </Box>
        </Box>
      </KeyboardAwareScrollView>
    </UTitleSubtitleWrapper>
  );
};

export default RegistrationPage;
