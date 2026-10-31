export function getAuthSession(): Promise<string | null>;
export function saveAuthSession(value: string): Promise<void>;
export function clearAuthSession(): Promise<void>;
