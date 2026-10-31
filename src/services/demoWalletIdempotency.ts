import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

const STORAGE_PREFIX = '@ubanku/demo-wallet-operation:';

export async function getDemoWalletOperationKey(operation: string): Promise<string> {
  const storageKey = `${STORAGE_PREFIX}${operation}`;
  const existing = await AsyncStorage.getItem(storageKey);
  if (existing) return existing;
  const created = Crypto.randomUUID();
  await AsyncStorage.setItem(storageKey, created);
  return created;
}

export async function clearDemoWalletOperationKey(operation: string): Promise<void> {
  await AsyncStorage.removeItem(`${STORAGE_PREFIX}${operation}`);
}
