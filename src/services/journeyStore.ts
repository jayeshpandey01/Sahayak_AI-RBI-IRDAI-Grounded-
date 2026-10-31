import AsyncStorage from '@react-native-async-storage/async-storage';

export type JourneyStatus = 'not_started' | 'in_progress' | 'ready_to_review' | 'submitted';
export type LoanJourney = {
  id: string;
  status: JourneyStatus;
  amount: string;
  monthlyIncome: string;
  employment: string;
  existingEmi: string;
  tenureMonths: number;
  annualRate: number;
  documents: Record<string, boolean>;
  consentToPrepare: boolean;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
  backendJourneyId?: string;
  backendStage?: string;
  selectedOfferId?: string;
  selectedOfferName?: string;
  estimatedEmi?: number;
  remoteDocumentIds?: string[];
  documentsPrepared?: boolean;
};

const KEY_PREFIX = '@sahayak/loan-journey-v2:';
const storageKey = (userId: string) => `${KEY_PREFIX}${userId}`;
let saveQueue: Promise<unknown> = Promise.resolve();
const initialJourney = (): LoanJourney => ({
  id: 'personal-loan-demo', status: 'not_started', amount: '', monthlyIncome: '',
  employment: '', existingEmi: '0', tenureMonths: 24, annualRate: 14,
  documents: {identity: false, income: false, bank: false}, consentToPrepare: false,
  createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
  backendStage: 'INTENT_CAPTURED', remoteDocumentIds: [], documentsPrepared: false,
});

export async function loadJourney(userId: string): Promise<LoanJourney> {
  try {
    const raw = await AsyncStorage.getItem(storageKey(userId));
    return raw ? {...initialJourney(), ...JSON.parse(raw)} : initialJourney();
  } catch {
    return initialJourney();
  }
}

export async function saveJourney(userId: string, update: Partial<LoanJourney>): Promise<LoanJourney> {
  const task = saveQueue.then(async () => {
    const current = await loadJourney(userId);
    const next = {...current, ...update, updatedAt: new Date().toISOString()};
    await AsyncStorage.setItem(storageKey(userId), JSON.stringify(next));
    return next;
  });
  saveQueue = task.then(() => undefined, () => undefined);
  return task;
}

export function estimateLoan(amount: number, annualRate: number, months: number) {
  if (!Number.isFinite(amount) || amount <= 0 || months <= 0) return {emi: 0, total: 0, interest: 0};
  const monthlyRate = annualRate / 1200;
  const emi = monthlyRate === 0 ? amount / months : amount * monthlyRate * Math.pow(1 + monthlyRate, months) / (Math.pow(1 + monthlyRate, months) - 1);
  const roundedEmi = Math.round(emi);
  const total = roundedEmi * months;
  return {emi: roundedEmi, total, interest: total - amount};
}
