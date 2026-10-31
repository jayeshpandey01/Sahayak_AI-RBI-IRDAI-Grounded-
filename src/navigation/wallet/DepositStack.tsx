import React from 'react';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {ParamListBase} from '@react-navigation/native';
import DepositPage from '../../screens/Wallet/DepositPage';
import DepositDetailsPage from '../../screens/Wallet/DepositDetailsPage';
import DepositConfirmPage from '../../screens/Wallet/DepositConfirmPage';

export type DepositStackParamList = ParamListBase & {};

const Stack = createNativeStackNavigator<DepositStackParamList>();

const DepositStack = () => {
  return (
    <Stack.Navigator
      initialRouteName="DepositPage"
      screenOptions={{headerShown: false}}>
      <Stack.Screen name="DepositPage" component={DepositPage} />
      <Stack.Screen name="DepositDetailsPage" component={DepositDetailsPage} />
      <Stack.Screen name="DepositConfirmPage" component={DepositConfirmPage} />

      {/* More screens to be added */}
    </Stack.Navigator>
  );
};

export default DepositStack;
