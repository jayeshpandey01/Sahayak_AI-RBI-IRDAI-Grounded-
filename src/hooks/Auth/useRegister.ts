import {AxiosInstance} from 'axios';
import useApiRequest from './useApiRequest';
import iRegisterNewUserData from '../../interfaces/Auth/iRegisterNewUserData';
import useDeviceTrust from './useDeviceTrust';

const useRegister = (
  api: AxiosInstance,
  setAuthToken: any,
  setUser: any,
  setIsAuthenticated: any,
) => {
  const {deviceToken, regenerateToken} = useDeviceTrust();

  // const {setAuthToken, setUser, setIsAuthenticated} = useContext(AuthContext);
  const [registerRequest, registerLoading, registerError] = useApiRequest(
    api,
    '/auth/register',
    'POST',
  );

  const register = async (userData: iRegisterNewUserData) => {
    try {
      const response = await registerRequest({
        ...userData,
        device_info: {device_id: deviceToken},
      });

      if (response && response.registerUserDataRes?.access_token) {
        setAuthToken(response.registerUserDataRes.access_token);
        setUser({
          id: String(response.registerUserDataRes.id),
          email: userData.email || '',
          full_name: userData.first_name || null,
        });
        setIsAuthenticated(true);
      }
      await regenerateToken();
      return response;
    } catch (error) {
      throw error;
    }
  };
  return [register, registerLoading, registerError];
};

export default useRegister;
