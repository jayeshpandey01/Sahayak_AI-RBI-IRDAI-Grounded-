import * as Crypto from 'expo-crypto';

let deviceToken: string | null = null;

const createToken = () =>
  Array.from(Crypto.getRandomBytes(32), byte =>
    byte.toString(16).padStart(2, '0'),
  ).join('');

export const getDeviceToken = async () => {
  if (!deviceToken) {
    deviceToken = createToken();
  }
  return deviceToken;
};

export const regenerateDeviceToken = async () => {
  deviceToken = createToken();
  return deviceToken;
};

export const deleteDeviceToken = async () => {
  deviceToken = null;
};
