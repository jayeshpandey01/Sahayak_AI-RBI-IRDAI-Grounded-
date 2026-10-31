import React, {useCallback, useState} from 'react';
import {ActivityIndicator} from 'react-native';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import {Alert, Box, Button, HStack, Pressable, ScrollView, Text, VStack} from 'native-base';
import {MaterialCommunityIcons} from '@expo/vector-icons';
import {useAuth} from '../contexts/AuthContext';
import {apiErrorMessage} from '../services/apiClient';
import {getUserLoans, runLoanAudit, seedDemoLoans, LoanAuditReport, UserLoan} from '../services/sahayakApi';

const ink = '#17343A';
const muted = '#61777B';
const teal = '#087F78';
const surface = '#F5F8F7';
const money = (value: number) => `₹${Math.round(Number(value) || 0).toLocaleString('en-IN')}`;

export default function LoanPortfolioScreen() {
  const navigation = useNavigation<any>();
  const {authToken} = useAuth();
  const [loans, setLoans] = useState<UserLoan[]>([]);
  const [audit, setAudit] = useState<LoanAuditReport>();
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    if (!authToken) {
      setLoans([]);
      setAudit(undefined);
      setLoading(false);
      setError('Sign in to view and track loans.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const items = await getUserLoans(authToken);
      setLoans(items);
      setAudit(items.length ? await runLoanAudit(authToken) : undefined);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  useFocusEffect(useCallback(() => {
    refresh().catch(() => undefined);
  }, [refresh]));

  const loadSamples = async () => {
    if (!authToken) return;
    setSeeding(true);
    setError('');
    try {
      const items = await seedDemoLoans(authToken);
      setLoans(items);
      setAudit(items.length ? await runLoanAudit(authToken) : undefined);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSeeding(false);
    }
  };

  const nextDue = [...loans]
    .filter(loan => loan.status === 'ACTIVE' || loan.status === 'OVERDUE')
    .sort((a, b) => a.next_due_date.localeCompare(b.next_due_date))[0];

  return <Box flex={1} bg={surface} safeArea>
    <ScrollView px={5} pb={8} showsVerticalScrollIndicator={false}>
      <Box maxW={620} w="100%" alignSelf="center">
        <HStack alignItems="center" justifyContent="space-between" mt={3} mb={5}>
          <VStack>
            <Text color={teal} fontSize="xs" bold letterSpacing="2">SAHAYAK AI</Text>
            <Text color={ink} fontSize="2xl" bold>Loan tracker</Text>
          </VStack>
          <Pressable onPress={() => navigation.navigate('UserMenu')} accessibilityRole="button" accessibilityLabel="Open profile" p={2}>
            <MaterialCommunityIcons name="account-circle-outline" size={29} color={teal}/>
          </Pressable>
        </HStack>

        <Box bg={ink} p={5} rounded="2xl" mb={4}>
          <Text color="#A9DCD3" fontSize="xs" bold letterSpacing="1">YOUR LOAN OVERVIEW</Text>
          {loading ? <ActivityIndicator color="white" style={{marginVertical: 22}}/> : <>
            <Text color="white" fontSize="3xl" bold mt={2}>{money(audit?.total_outstanding_principal || 0)}</Text>
            <Text color="#D4E3E1" fontSize="sm">Outstanding balance · {loans.length} tracked {loans.length === 1 ? 'loan' : 'loans'}</Text>
            <HStack mt={5} space={3}>
              <Box flex={1} bg="#29484D" p={3} rounded="lg">
                <Text color="#A9DCD3" fontSize="xs">MONTHLY EMI</Text>
                <Text color="white" fontSize="lg" bold mt={1}>{money(audit?.total_monthly_emi || 0)}</Text>
              </Box>
              <Box flex={1} bg="#29484D" p={3} rounded="lg">
                <Text color="#A9DCD3" fontSize="xs">NEXT DUE</Text>
                <Text color="white" fontSize="lg" bold mt={1}>{nextDue?.next_due_date || '—'}</Text>
              </Box>
            </HStack>
          </>}
        </Box>

        <Alert status="info" mb={4} rounded="xl">
          <Alert.Icon />
          <Text color={ink} fontSize="xs" flex={1}>Demo accounts are marked simulated. User-entered details are not verified with lenders. This tracker does not record payments or change wallet balances.</Text>
        </Alert>

        {error ? <Alert status="error" mb={4} rounded="lg"><Alert.Icon/><Text flex={1}>{error}</Text><Button size="sm" variant="ghost" onPress={refresh}>Retry</Button></Alert> : null}

        {!loading && !error && loans.length === 0 ? <Box bg="white" p={5} rounded="2xl" mb={4}>
          <Text color={ink} fontSize="lg" bold>No loans to track yet</Text>
          <Text color={muted} mt={2} mb={4}>Load a sample portfolio to explore balances, EMI due dates, and loan audit insights.</Text>
          <Button bg={teal} isLoading={seeding} onPress={loadSamples} _text={{color: 'white', bold: true}}>Load sample loans</Button>
        </Box> : null}

        {!loading && loans.length > 0 ? <>
          <HStack justifyContent="space-between" alignItems="center" mb={3}>
            <Text color={ink} fontSize="lg" bold>Tracked loans</Text>
            <Button size="sm" variant="outline" borderColor="#C9D8D5" onPress={refresh} _text={{color: teal}}>Refresh</Button>
          </HStack>
          <VStack space={3} mb={5}>
            {loans.map(loan => <Box key={loan.id} bg="white" p={4} rounded="xl">
              <HStack justifyContent="space-between" alignItems="flex-start">
                <VStack flex={1}>
                  <Text color={ink} bold fontSize="md">{loan.lender_name}</Text>
                  <Text color={muted} fontSize="xs">{loan.loan_type.replace('_', ' ')} · {loan.account_number}</Text>
                </VStack>
                <Text color={loan.status === 'OVERDUE' ? '#B54708' : teal} fontSize="xs" bold>{loan.status}</Text>
              </HStack>
              <HStack mt={4} space={3}>
                <Metric label="OUTSTANDING" value={money(loan.outstanding_principal)}/>
                <Metric label="MONTHLY EMI" value={money(loan.emi_amount)}/>
                <Metric label="RATE" value={`${loan.interest_rate_percent}%`}/>
              </HStack>
              <Text color={muted} fontSize="xs" mt={3}>Next due {loan.next_due_date} · {loan.remaining_tenure_months} installments left</Text>
              <Text color="#8A5B15" fontSize="xs" mt={1}>{loan.notes?.startsWith('SIMULATED DEMO DATA ONLY') ? `SIMULATED · ${loan.notes.replace(/^SIMULATED DEMO DATA ONLY — /, '')}` : 'USER-ENTERED · Not verified with lender'}</Text>
            </Box>)}
          </VStack>

          {audit ? <Box bg="white" p={5} rounded="2xl" mb={4}>
            <Text color={ink} fontSize="lg" bold>Portfolio snapshot</Text>
            <HStack justifyContent="space-between" mt={4}><Text color={muted}>Total original principal</Text><Text color={ink} bold>{money(audit.total_borrowed_principal)}</Text></HStack>
            <HStack justifyContent="space-between" mt={2}><Text color={muted}>EMI / assumed ₹50k demo income</Text><Text color={ink} bold>{audit.foir_percent}%</Text></HStack>
            <HStack justifyContent="space-between" mt={2}><Text color={muted}>Active loans</Text><Text color={ink} bold>{audit.active_loans_count}</Text></HStack>
            <Text color={muted} fontSize="xs" mt={3}>This ratio uses an assumed ₹50,000 monthly income. It is a demo estimate, not personal affordability advice or a lending decision.</Text>
          </Box> : null}
        </> : null}

        <Button mb={3} bg={teal} onPress={() => navigation.navigate('LoanJourney')} _text={{color: 'white', bold: true}}>Explore loan readiness</Button>
        <Button variant="ghost" onPress={() => navigation.navigate('ChatTab')} _text={{color: teal}}>Ask Sahayak AI about loans</Button>
      </Box>
    </ScrollView>
  </Box>;
}

function Metric({label, value}: {label: string; value: string}) {
  return <VStack flex={1}>
    <Text color={muted} fontSize="2xs" bold>{label}</Text>
    <Text color={ink} fontSize="sm" bold mt={1}>{value}</Text>
  </VStack>;
}
