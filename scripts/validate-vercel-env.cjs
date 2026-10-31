const configuredApiUrl = process.env.EXPO_PUBLIC_API_BASE_URL;

if (!configuredApiUrl) {
  console.error(
    'Set EXPO_PUBLIC_API_BASE_URL in the Vercel project environment before building the web app.',
  );
  process.exit(1);
}

try {
  const apiUrl = new URL(configuredApiUrl);
  if (apiUrl.protocol !== 'https:' || ['localhost', '127.0.0.1'].includes(apiUrl.hostname)) {
    throw new Error('The API URL must be a public HTTPS URL.');
  }
} catch (error) {
  console.error(`Invalid EXPO_PUBLIC_API_BASE_URL: ${error.message}`);
  process.exit(1);
}
