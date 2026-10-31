import {formatRupees, formatCurrency} from '../src/utils/currency';
import {formatNumberCO} from '../src/utils/formatNumberCO';

describe('Currency and Rupee Formatting', () => {
  it('formats positive numbers according to Indian numbering system', () => {
    expect(formatRupees(1000)).toBe('1,000');
    expect(formatRupees(20000)).toBe('20,000');
    expect(formatRupees(150000)).toBe('1,50,000');
    expect(formatRupees(1000000)).toBe('10,00,000');
  });

  it('formats zero correctly', () => {
    expect(formatRupees(0)).toBe('0');
  });

  it('formatCurrency prepends Rupee symbol', () => {
    expect(formatCurrency(20000)).toBe('₹ 20,000');
    expect(formatCurrency(-25000)).toBe('-₹ 25,000');
  });

  it('formatNumberCO backwards compatible alias delegates to formatRupees', () => {
    expect(formatNumberCO(20000)).toBe('20,000');
    expect(formatNumberCO(150000)).toBe('1,50,000');
  });
});

