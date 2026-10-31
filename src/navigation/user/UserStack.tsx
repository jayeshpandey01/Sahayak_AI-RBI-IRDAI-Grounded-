import React from 'react';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import UserPage from '../../screens/User/UserPage';
import ReferralsPage from '../../screens/User/ReferralsPage';
import LanguageSettingsPage from '../../screens/User/LanguageSettingsPage';
import ProfileDetailsPage from '../../screens/User/ProfileDetailsPage';

const Stack = createNativeStackNavigator();

const UserStack = () => {
  return (
    <Stack.Navigator
      initialRouteName="UserPage"
      screenOptions={{
        headerShown: false,
      }}>
      <Stack.Screen name="UserPage" component={UserPage} />
      <Stack.Screen name="ProfileDetailsPage" component={ProfileDetailsPage} />
      <Stack.Screen name="ReferralsPage" component={ReferralsPage} />
      <Stack.Screen name="LanguageSettingsPage" component={LanguageSettingsPage} />
    </Stack.Navigator>
  );
};

export default UserStack;
