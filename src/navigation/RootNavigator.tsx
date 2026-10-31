import React from 'react';
import TabNavigator from './TabNavigator';
import SendStack from './wallet/SendNavigator';
import WalletStack from './wallet/WalletStack';
import DepositStack from './wallet/DepositStack';
import WithdrawStack from './wallet/WithdrawStack';
import UserStack from './user/UserStack';
import {LoanJourneyScreen} from '../screens/SahayakJourney';
import SahayakChatScreen from '../screens/SahayakChatScreen';
import FundDemoWalletPage from '../screens/Wallet/FundDemoWalletPage';
import ReceiveDemoMoneyPage from '../screens/Wallet/ReceiveDemoMoneyPage';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
// import ReloadScreen from '../screens/Reload';  //

const RootStack = createNativeStackNavigator();

const RootNavigator = () => {
  return (
    <RootStack.Navigator screenOptions={{headerShown: false}}>
      <RootStack.Screen name="Tabs" component={TabNavigator} />
      <RootStack.Screen name="Chat" component={SahayakChatScreen} />
      <RootStack.Screen name="LoanJourney" component={LoanJourneyScreen} />
      <RootStack.Screen name="Send" component={SendStack} />
      <RootStack.Screen name="Wallet" component={WalletStack} />
      <RootStack.Screen name="Deposit" component={DepositStack} />
      <RootStack.Screen name="Withdraw" component={WithdrawStack} />
      <RootStack.Screen name="FundDemoWallet" component={FundDemoWalletPage} />
      <RootStack.Screen name="ReceiveDemoMoney" component={ReceiveDemoMoneyPage} />
      <RootStack.Screen name="UserMenu" component={UserStack} />
    </RootStack.Navigator>
  );
};

export default RootNavigator;
