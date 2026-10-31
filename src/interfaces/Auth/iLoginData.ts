import iDeviceInfo from './iDeviceInfo';
import iPhoneData from './iPhoneData';

export default interface iLoginData extends iPhoneData, Partial<iDeviceInfo> {
  pin: string;
}
