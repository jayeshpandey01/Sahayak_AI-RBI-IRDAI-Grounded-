export function formatRupees(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Math.abs(value));
}

export function formatCurrency(value: number, prefix: string = '₹'): string {
  const formatted = formatRupees(value);
  const sign = value < 0 ? '-' : '';
  return `${sign}${prefix} ${formatted}`;
}

export default formatRupees;

