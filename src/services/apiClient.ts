import axios from 'axios';
import {Platform} from 'react-native';

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ||
  (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {'Content-Type': 'application/json'},
  timeout: 15000,
});

export function authHeaders(token?: string) {
  return token ? {Authorization: `Bearer ${token}`} : {};
}

export function apiErrorMessage(error: any): string {
  const detail = error?.response?.data?.detail;
  if (error?.response?.status === 404 && (!detail || detail === 'Not Found')) {
    if (String(error?.config?.url || '').includes('/api/v1/demo-wallet')) {
      return 'The backend at this address is missing the demo wallet route. Restart or redeploy it from the current project code.';
    }
    return 'This backend route was not found. Check that the app and backend are running compatible project versions.';
  }
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg || item.issue).filter(Boolean).join('\n');
  if (!error?.response) {
    return `Cannot reach the backend at ${API_BASE_URL}. Start the backend on port 8000 and check that this device can reach that address.`;
  }
  return error?.message || 'The service is unavailable. Check the backend address and try again.';
}
