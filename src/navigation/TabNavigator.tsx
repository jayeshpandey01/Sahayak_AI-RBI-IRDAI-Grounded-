import React from 'react';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {MaterialCommunityIcons} from '@expo/vector-icons';
import HomeWallet from '../screens/HomeWallet';
import Home from '../screens/Home';
import SahayakJourney from '../screens/SahayakJourney';
import SahayakChatScreen from '../screens/SahayakChatScreen';
import LoanPortfolioScreen from '../screens/LoanPortfolioScreen';
import BillScheduleScreen from '../screens/BillScheduleScreen';
import {useLanguage} from '../contexts/LanguageContext';

const Tab = createBottomTabNavigator();

const TabNavigator = () => {
  const {t} = useLanguage();

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarShowLabel: false,
        tabBarActiveTintColor: '#087F78',
        tabBarInactiveTintColor: '#61777B',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopColor: '#E2E8F0',
          borderTopWidth: 1,
          elevation: 8,
          shadowColor: '#000000',
          shadowOffset: {width: 0, height: -2},
          shadowOpacity: 0.06,
          shadowRadius: 8,
          height: 60,
          paddingTop: 0,
          paddingBottom: 0,
        },
        tabBarItemStyle: {
          cursor: 'pointer' as any,
          justifyContent: 'center',
          alignItems: 'center',
          height: 60,
        },
      }}>
      <Tab.Screen
        name="Home"
        component={SahayakJourney}
        options={{
          tabBarLabel: t('journey') || 'Journey',
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'compass' : 'compass-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
      <Tab.Screen
        name="LoansTab"
        component={LoanPortfolioScreen}
        options={{
          tabBarLabel: 'Loans',
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'bank' : 'bank-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
      <Tab.Screen
        name="BillsTab"
        component={BillScheduleScreen}
        options={{
          tabBarLabel: t('billSchedules'),
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'calendar-clock' : 'calendar-clock-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
      <Tab.Screen
        name="ChatTab"
        component={SahayakChatScreen}
        options={{
          tabBarLabel: t('chat') || 'Chat',
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'chat-processing' : 'chat-processing-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
      <Tab.Screen
        name="WalletTab"
        component={HomeWallet}
        options={{
          tabBarLabel: t('wallet') || 'Wallet',
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'wallet' : 'wallet-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
      {/* Existing Ubanku home remains available as the original demo screen. */}
      <Tab.Screen
        name="UbankuHome"
        component={Home}
        options={{
          tabBarLabel: 'Ubanku',
          tabBarIcon: ({color, focused}) => (
            <MaterialCommunityIcons
              name={focused ? 'credit-card' : 'credit-card-outline'}
              size={focused ? 28 : 26}
              color={color}
            />
          ),
        }}
      />
    </Tab.Navigator>
  );
};

export default TabNavigator;
