import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

const DEVICE_TOKEN_KEY = 'ubanku-device-trust-token';

const createToken = () =>
  Array.from(Crypto.getRandomBytes(32), byte =>
    byte.toString(16).padStart(2, '0'),
  ).join('');

export const getDeviceToken = async () => {
  const storedToken = await SecureStore.getItemAsync(DEVICE_TOKEN_KEY);
  if (storedToken) {
    return storedToken;
  }

  const token = createToken();
  await SecureStore.setItemAsync(DEVICE_TOKEN_KEY, token);
  return token;
};

export const regenerateDeviceToken = async () => {
  const token = createToken();
  await SecureStore.setItemAsync(DEVICE_TOKEN_KEY, token);
  return token;
};

export const deleteDeviceToken = () =>
  SecureStore.deleteItemAsync(DEVICE_TOKEN_KEY);
