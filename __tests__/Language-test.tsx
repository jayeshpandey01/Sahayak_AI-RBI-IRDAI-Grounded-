import React from 'react';
import renderer, {act} from 'react-test-renderer';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {LanguageProvider, useLanguage} from '../src/contexts/LanguageContext';

describe('LanguageContext', () => {
  let currentLangContext: ReturnType<typeof useLanguage>;

  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  const TestConsumer = () => {
    currentLangContext = useLanguage();
    return null;
  };

  it('defaults to English', async () => {
    await act(async () => {
      renderer.create(
        <LanguageProvider>
          <TestConsumer />
        </LanguageProvider>,
      );
    });

    expect(currentLangContext.currentLanguage).toBe('en');
    expect(currentLangContext.t('wallet')).toBe('Wallet');
    expect(currentLangContext.t('deposit')).toBe('Deposit');
    expect(currentLangContext.getGreeting('Andy')).toBe('Hello, Andy!');
  });

  it('switches to Hindi', async () => {
    await act(async () => {
      renderer.create(
        <LanguageProvider>
          <TestConsumer />
        </LanguageProvider>,
      );
    });

    await act(async () => {
      await currentLangContext.setLanguage('hi');
    });

    expect(currentLangContext.currentLanguage).toBe('hi');
    expect(currentLangContext.t('wallet')).toBe('वॉलेट');
    expect(currentLangContext.t('deposit')).toBe('जमा करें');
    expect(currentLangContext.getGreeting('Andy')).toBe('नमस्ते, Andy!');
  });

  it('switches to Marathi', async () => {
    await act(async () => {
      renderer.create(
        <LanguageProvider>
          <TestConsumer />
        </LanguageProvider>,
      );
    });

    await act(async () => {
      await currentLangContext.setLanguage('mr');
    });

    expect(currentLangContext.currentLanguage).toBe('mr');
    expect(currentLangContext.t('wallet')).toBe('वॉलेट');
    expect(currentLangContext.t('deposit')).toBe('पैसे भरा');
    expect(currentLangContext.getGreeting('Andy')).toBe('नमस्कार, Andy!');
  });

  it('interpolates dynamic user names with getGreeting', async () => {
    await act(async () => {
      renderer.create(
        <LanguageProvider>
          <TestConsumer />
        </LanguageProvider>,
      );
    });

    // English
    await act(async () => {
      await currentLangContext.setLanguage('en');
    });
    expect(currentLangContext.getGreeting('Pooja')).toBe('Hello, Pooja!');
    expect(currentLangContext.getGreeting()).toBe('Hello!');

    // Hindi
    await act(async () => {
      await currentLangContext.setLanguage('hi');
    });
    expect(currentLangContext.getGreeting('Pooja')).toBe('नमस्ते, Pooja!');
    expect(currentLangContext.getGreeting()).toBe('नमस्ते!');

    // Marathi
    await act(async () => {
      await currentLangContext.setLanguage('mr');
    });
    expect(currentLangContext.getGreeting('Pooja')).toBe('नमस्कार, Pooja!');
    expect(currentLangContext.getGreeting()).toBe('नमस्कार!');
  });
});
