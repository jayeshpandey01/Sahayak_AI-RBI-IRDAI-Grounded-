import {AppRegistry} from 'react-native';
import App from './App';
import {expo as expoConfig} from './app.json';
import {enableScreens} from 'react-native-screens';

enableScreens();

AppRegistry.registerComponent(expoConfig.name, () => App);
