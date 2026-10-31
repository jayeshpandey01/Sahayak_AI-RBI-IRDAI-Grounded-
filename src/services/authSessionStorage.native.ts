import * as SecureStore from 'expo-secure-store';
const KEY = 'sahayak-auth-session-v1';
export const getAuthSession = () => SecureStore.getItemAsync(KEY);
export const saveAuthSession = (value: string) => SecureStore.setItemAsync(KEY, value);
export const clearAuthSession = () => SecureStore.deleteItemAsync(KEY);
