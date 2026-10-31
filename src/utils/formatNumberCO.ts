import {formatRupees} from './currency';

export function formatNumberCO(value: number): string {
  return formatRupees(value);
}

export {formatRupees};
export default formatNumberCO;
