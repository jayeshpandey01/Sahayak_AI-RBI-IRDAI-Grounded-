import React, {useState} from 'react';
import {Box, Button, FormControl, Input, Text, VStack} from 'native-base';
import {KeyboardAvoidingView, Platform} from 'react-native';
import {useAuth} from '../../contexts/AuthContext';
import {apiErrorMessage} from '../../services/apiClient';

const ink = '#17343A';
const teal = '#087F78';

const EmailAuthScreen = () => {
  const {loginAccount, registerAccount} = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError('');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {setError('Enter a valid email address.'); return;}
    if (password.length < 8) {setError('Password must be at least 8 characters.'); return;}
    if (mode === 'register' && !fullName.trim()) {setError('Enter your name.'); return;}
    setBusy(true);
    try {
      const credentials = {email, password, full_name: fullName};
      if (mode === 'register') await registerAccount(credentials);
      else await loginAccount(credentials);
    } catch (requestError) {setError(apiErrorMessage(requestError));}
    finally {setBusy(false);}
  };

  return <KeyboardAvoidingView style={{flex: 1}} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <Box flex={1} safeArea bg="#F5F8F7" justifyContent="center" px={6}>
      <VStack space={5}>
        <VStack space={1}>
          <Text color={teal} fontSize="xs" bold letterSpacing="2">SAHAYAK AI</Text>
          <Text color={ink} fontSize="3xl" bold>{mode === 'login' ? 'Welcome back' : 'Create your account'}</Text>
          <Text color="#61777B">Sign in to save and continue your financial journey.</Text>
        </VStack>
        {mode === 'register' && <FormControl><FormControl.Label>Full name</FormControl.Label><Input testID="auth-name" accessibilityLabel="Full name" value={fullName} onChangeText={setFullName} autoCapitalize="words" bg="white" /></FormControl>}
        <FormControl><FormControl.Label>Email</FormControl.Label><Input testID="auth-email" accessibilityLabel="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" bg="white" /></FormControl>
        <FormControl><FormControl.Label>Password</FormControl.Label><Input testID="auth-password" accessibilityLabel="Password" value={password} onChangeText={setPassword} type="password" autoComplete={mode === 'register' ? 'new-password' : 'password'} bg="white" /></FormControl>
        {error ? <Text accessibilityRole="alert" color="error.600">{error}</Text> : null}
        <Button testID="auth-submit" bg={teal} isLoading={busy} onPress={submit} _text={{bold: true}}>{mode === 'login' ? 'Sign in' : 'Create account'}</Button>
        <Button variant="ghost" onPress={() => {setError(''); setMode(mode === 'login' ? 'register' : 'login');}} _text={{color: ink}}>{mode === 'login' ? 'New here? Create an account' : 'Already registered? Sign in'}</Button>
        <Text color="#718489" fontSize="xs" textAlign="center">Demo accounts use the local Sahayak API. This app does not provide lender approval.</Text>
      </VStack>
    </Box>
  </KeyboardAvoidingView>;
};

export default EmailAuthScreen;
