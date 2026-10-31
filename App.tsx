import React, {useState} from 'react';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import {NativeBaseProvider} from 'native-base';
import {NavigationContainer} from '@react-navigation/native';
import AuthNavigator from './src/navigation/AuthNavigator';
import {AuthProvider, useAuth} from './src/contexts/AuthContext';
import {LanguageProvider} from './src/contexts/LanguageContext';
import {themeV1} from './src/theme/v1';
import RootNavigator from './src/navigation/RootNavigator';
import LaunchScreen from './src/screens/Auth/LaunchScreen';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import ResponsiveAppContainer from './src/components/layout/ResponsiveAppContainer';

const AppContent = () => {
  const {isAuthenticated, isAuthReady} = useAuth();
  const [isAppReady, setIsAppReady] = useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => setIsAppReady(true), 333);
    return () => clearTimeout(timer);
  }, []);

  if (!isAppReady || !isAuthReady) {
    return (
      <ResponsiveAppContainer>
        <LaunchScreen />
      </ResponsiveAppContainer>
    );
  } else {
    return (
      <ResponsiveAppContainer>
        <NavigationContainer>
          {isAuthenticated ? <RootNavigator /> : <AuthNavigator />}
        </NavigationContainer>
      </ResponsiveAppContainer>
    );
  }
};

const App = () => {
  return (
    <SafeAreaProvider>
      <GestureHandlerRootView style={{flex: 1}}>
        <NativeBaseProvider theme={themeV1}>
          <LanguageProvider>
            <AuthProvider>
              <AppContent />
            </AuthProvider>
          </LanguageProvider>
        </NativeBaseProvider>
      </GestureHandlerRootView>
    </SafeAreaProvider>
  );
};

export default App;
