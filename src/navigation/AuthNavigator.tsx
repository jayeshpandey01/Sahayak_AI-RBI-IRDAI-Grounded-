import {createNativeStackNavigator} from '@react-navigation/native-stack';
import EmailAuthScreen from '../screens/Auth/EmailAuthScreen';
import {ParamListBase} from '@react-navigation/native';
import iRegisterPhoneData from '../interfaces/Auth/iRegisterPhoneData';
import iRegisterNewUserData from '../interfaces/Auth/iRegisterNewUserData';

// Kept for legacy phone-flow screens that remain in the source tree.
export type RootStackParamList = ParamListBase & {
  VerificationMessage: {phoneNumber: iRegisterPhoneData; newUser: boolean};
  VerificationPage: {phoneNumber: iRegisterPhoneData; newUser: boolean};
  RegistrationPage: {phoneNumber: iRegisterPhoneData};
  CreatePinPage: {newUserData: iRegisterNewUserData};
  TrustInDevice: {phoneNumber: iRegisterPhoneData};
  EnterCustomPin: {phoneNumber: iRegisterPhoneData; trustInDevice: boolean};
  ForgotPinVerification: {phoneNumber: iRegisterPhoneData};
  ChangePinPage: {phoneNumber: iRegisterPhoneData; verificationCode: string};
};

const Stack = createNativeStackNavigator();

const AuthNavigator = () => {
  return (
    <Stack.Navigator
      initialRouteName="EmailAuth"
      screenOptions={{headerShown: false}}>
      <Stack.Screen name="EmailAuth" component={EmailAuthScreen} />
    </Stack.Navigator>
  );
};

export default AuthNavigator;
