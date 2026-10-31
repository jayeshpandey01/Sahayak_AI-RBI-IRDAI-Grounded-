import React, {createContext, useState, useContext, useEffect} from 'react';
import axios from 'axios';
import {getAuthSession, saveAuthSession, clearAuthSession} from '../services/authSessionStorage';
import useRegister from '../hooks/Auth/useRegister';
import useSendVerificationCode from '../hooks/Auth/useSendVerificationCode';
import useVerificationCode from '../hooks/Auth/useVerificationCode';
import useIsRegistered from '../hooks/Auth/useIsRegistered';
import useGetReferredCode from '../hooks/Auth/useGetReferredCode';
import useGetUserByReferredCode from '../hooks/Auth/useGetUserByReferredCode';
import useLogin from '../hooks/Auth/useLogin';
import useChangePassword from '../hooks/Auth/useChangePassword';
import iUser from '../interfaces/Auth/iRegisterNewUserData';
import iPhoneData from '../interfaces/Auth/iPhoneData';
import iLoginData from '../interfaces/Auth/iLoginData';
import iMsgReq from '../interfaces/Auth/iMsgReq';
import iChangePassReq from '../interfaces/Auth/iChangePassReq';
import {API_BASE_URL, apiClient, authHeaders} from '../services/apiClient';
import UserProfile from '../interfaces/Auth/iUserProfile';

type AccountPayload = {email: string; password: string; full_name?: string};

interface CodeData extends iPhoneData {
  type?: string;
  code?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  authToken: string;
  register: (userData: iUser) => Promise<any>;
  registerAccount: (data: AccountPayload) => Promise<any>;
  loginAccount: (data: AccountPayload) => Promise<any>;
  updateProfile: (data: {full_name: string}) => Promise<UserProfile>;
  sendVerificationCode: (data: iMsgReq) => Promise<any>;
  checkVerificationCode: (data: iMsgReq) => Promise<any>;
  isRegistered: (data: CodeData) => Promise<any>;
  getReferredCode: (data: CodeData) => Promise<any>;
  getUserByReferredCode: (referredCode: string) => Promise<any>;
  login: (data: iLoginData, trustInDevice: boolean) => Promise<any>;
  loginError: string | null;
  changePassword: (data: iChangePassReq) => Promise<any>;
  isAuthenticated: boolean;
  isAuthReady: boolean;
  logout: () => void;
  setIsAuthenticated: (value: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({children}: any) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authToken, setAuthToken] = useState<string>('');
  const [isAuthReady, setIsAuthReady] = useState(false);

  useEffect(() => {
    let active = true;
    getAuthSession().then(async raw => {
      if (!active) return;
      if (raw) {
        const session = JSON.parse(raw);
        if (session?.token) {
          try {
            const response = await apiClient.get('/api/auth/me', {headers: authHeaders(session.token)});
            if (response.data?.id) {
              const profile: UserProfile = {
                id: String(response.data.id),
                email: String(response.data.email || ''),
                full_name: response.data.full_name || null,
                role: response.data.role || 'borrower',
                auth_provider: response.data.auth_provider || 'email',
                is_active: response.data.is_active ?? true,
                created_at: response.data.created_at,
              };
              setAuthToken(session.token);
              setUser(profile);
              setIsAuthenticated(true);
            } else {
              await clearAuthSession();
            }
          } catch (error) {
            const status = axios.isAxiosError(error) ? error.response?.status : undefined;
            if (status === 401 || status === 403) {
              // The backend explicitly rejected this session. Do not restore a
              // cached identity with credentials that protected APIs reject.
              await clearAuthSession();
              if (active) {
                setAuthToken('');
                setUser(null);
                setIsAuthenticated(false);
              }
            } else if (session.user) {
              // Keep the cached session only when the backend could not be
              // reached (for example, while the device is offline).
              const cachedProfile: UserProfile = typeof session.user === 'object'
                ? session.user
                : {id: String(session.user), email: '', full_name: null};
              if (active) {
                setAuthToken(session.token);
                setUser(cachedProfile);
                setIsAuthenticated(true);
              }
            } else {
              await clearAuthSession();
            }
          }
        }
      }
    }).catch(() => undefined).finally(() => {if (active) setIsAuthReady(true);});
    return () => {active = false;};
  }, []);

  const acceptBackendSession = (data: any) => {
    if (!data?.access_token || !data?.user?.id) throw new Error('The authentication service returned an invalid session.');
    const profile: UserProfile = {
      id: String(data.user.id),
      email: String(data.user.email || ''),
      full_name: data.user.full_name || null,
      role: data.user.role || 'borrower',
      auth_provider: data.user.auth_provider || 'email',
      is_active: data.user.is_active ?? true,
      created_at: data.user.created_at,
    };
    setAuthToken(data.access_token);
    setUser(profile);
    setIsAuthenticated(true);
    return data;
  };

  const loginAccount = async (credentials: AccountPayload) => {
    const response = await apiClient.post('/api/auth/login', {email: credentials.email.trim().toLowerCase(), password: credentials.password});
    return acceptBackendSession(response.data);
  };

  const registerAccount = async (account: AccountPayload) => {
    const response = await apiClient.post('/api/auth/register', {email: account.email.trim().toLowerCase(), password: account.password, full_name: account.full_name?.trim() || undefined});
    return acceptBackendSession(response.data);
  };

  const updateProfile = async (updateData: {full_name: string}): Promise<UserProfile> => {
    const response = await apiClient.patch('/api/auth/me', updateData, {headers: authHeaders(authToken)});
    if (response.data?.id) {
      const updatedProfile: UserProfile = {
        id: String(response.data.id),
        email: String(response.data.email || ''),
        full_name: response.data.full_name || null,
        role: response.data.role || 'borrower',
        auth_provider: response.data.auth_provider || 'email',
        is_active: response.data.is_active ?? true,
        created_at: response.data.created_at,
      };
      setUser(updatedProfile);
      return updatedProfile;
    }
    throw new Error('Failed to update profile');
  };

  useEffect(() => {
    if (!isAuthReady) return;
    if (isAuthenticated && authToken && user) {
      saveAuthSession(JSON.stringify({token: authToken, user})).catch(() => undefined);
    } else if (!isAuthenticated) {
      clearAuthSession().catch(() => undefined);
    }
  }, [authToken, user, isAuthenticated, isAuthReady]);

  // Retired phone/PIN hooks remain for unreachable legacy screens. Keep their
  // requests on the same backend origin as the active email auth flow.
  const api = axios.create({
    baseURL: `${API_BASE_URL}/api`,
    headers: {
      'Content-Type': 'application/json',
    },
  });
  api.interceptors.request.use(config => {
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  });

  const [register] = useRegister(
    api,
    setAuthToken,
    setUser,
    setIsAuthenticated,
  );
  const [
    sendVerificationCode,
  ] = useSendVerificationCode(api);
  const [
    checkVerificationCode,
  ] = useVerificationCode(api);
  const [isRegistered] = useIsRegistered(api);
  const [getReferredCode] = useGetReferredCode(api);
  const [
    getUserByReferredCode,
  ] = useGetUserByReferredCode(api);
  const [login, , loginError] = useLogin(
    api,
    setAuthToken,
    setUser,
    setIsAuthenticated,
  );
  const [changePassword] = useChangePassword(api);

  const logout = () => {
    try {
      setUser(null);
      setAuthToken('');
      setIsAuthenticated(false);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        authToken,
        register,
        registerAccount,
        loginAccount,
        updateProfile,
        sendVerificationCode,
        checkVerificationCode,
        isRegistered,
        getReferredCode,
        getUserByReferredCode,
        login,
        loginError,
        changePassword,
        logout,
        isAuthenticated,
        isAuthReady,
        setIsAuthenticated,
      }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
