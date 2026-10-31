import AsyncStorage from '@react-native-async-storage/async-storage';
const KEY = '@sahayak-auth-session-v1';
export const getAuthSession = () => AsyncStorage.getItem(KEY);
export const saveAuthSession = (value: string) => AsyncStorage.setItem(KEY, value);
export const clearAuthSession = () => AsyncStorage.removeItem(KEY);
