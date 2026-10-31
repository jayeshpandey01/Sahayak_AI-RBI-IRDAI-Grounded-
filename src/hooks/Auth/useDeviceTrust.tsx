import {useEffect, useState} from 'react';
import {
  deleteDeviceToken,
  getDeviceToken,
  regenerateDeviceToken,
} from '../../services/deviceTrustStorage';

const useDeviceTrust = () => {
  const [deviceToken, setDeviceToken] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    getDeviceToken()
      .then(token => {
        if (isMounted) {
          setDeviceToken(token);
        }
      })
      .catch(error => {
        console.error('Unable to load device trust token', error);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const regenerateToken = async () => {
    const token = await regenerateDeviceToken();
    setDeviceToken(token);
  };

  const deleteToken = async () => {
    await deleteDeviceToken();
    setDeviceToken(null);
  };

  return {deviceToken, regenerateToken, deleteToken};
};

export default useDeviceTrust;
