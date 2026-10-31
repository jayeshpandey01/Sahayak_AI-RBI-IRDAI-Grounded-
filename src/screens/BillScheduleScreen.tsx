import React, {useCallback, useMemo, useState} from 'react';
import {ActivityIndicator} from 'react-native';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import {Alert, Box, Button, HStack, Input, Modal, Pressable, ScrollView, Select, Text, VStack} from 'native-base';
import {MaterialCommunityIcons} from '@expo/vector-icons';
import {useAuth} from '../contexts/AuthContext';
import {useLanguage} from '../contexts/LanguageContext';
import {apiErrorMessage} from '../services/apiClient';
import {
  BillCategory,
  BillFrequency,
  BillPaymentRecord,
  createRecurringBill,
  getBillPaymentHistory,
  getRecurringBills,
  recordBillPayment,
  RecurringBill,
  updateRecurringBill,
} from '../services/sahayakApi';

const ink = '#17343A';
const muted = '#61777B';
const teal = '#087F78';
const surface = '#F5F8F7';
const categories: Array<{value: BillCategory; labelKey: string}> = [
  {value: 'ELECTRICITY', labelKey: 'billElectricity'}, {value: 'RENT', labelKey: 'billRent'},
  {value: 'WATER', labelKey: 'billWater'}, {value: 'GAS', labelKey: 'billGas'},
  {value: 'INTERNET', labelKey: 'billInternet'}, {value: 'MOBILE', labelKey: 'billMobile'},
  {value: 'INSURANCE', labelKey: 'billInsurance'}, {value: 'SUBSCRIPTION', labelKey: 'billSubscription'},
  {value: 'OTHER', labelKey: 'billOther'},
];
const frequencies: Array<{value: BillFrequency; labelKey: string}> = [
  {value: 'WEEKLY', labelKey: 'frequencyWeekly'}, {value: 'MONTHLY', labelKey: 'frequencyMonthly'},
  {value: 'QUARTERLY', labelKey: 'frequencyQuarterly'}, {value: 'YEARLY', labelKey: 'frequencyYearly'},
];
const localToday = () => {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
};

export default function BillScheduleScreen() {
  const navigation = useNavigation<any>();
  const {authToken} = useAuth();
  const {t} = useLanguage();
  const [bills, setBills] = useState<RecurringBill[]>([]);
  const [history, setHistory] = useState<BillPaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPaused, setShowPaused] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [category, setCategory] = useState<BillCategory>('ELECTRICITY');
  const [payee, setPayee] = useState('');
  const [expectedAmount, setExpectedAmount] = useState('');
  const [frequency, setFrequency] = useState<BillFrequency>('MONTHLY');
  const [nextDueDate, setNextDueDate] = useState(localToday());
  const [reminderDays, setReminderDays] = useState('3');
  const [selectedBill, setSelectedBill] = useState<RecurringBill | null>(null);
  const [paidAmount, setPaidAmount] = useState('');

  const refresh = useCallback(async () => {
    if (!authToken) {
      setBills([]);
      setHistory([]);
      setLoading(false);
      setError('Sign in to manage bill schedules.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [items, payments] = await Promise.all([
        getRecurringBills(authToken, showPaused),
        getBillPaymentHistory(authToken),
      ]);
      setBills(items);
      setHistory(payments);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [authToken, showPaused]);

  useFocusEffect(useCallback(() => {
    refresh().catch(() => undefined);
  }, [refresh]));

  const dueSoonCount = useMemo(() => bills.filter(bill => ['DUE_SOON', 'DUE_TODAY'].includes(bill.due_status)).length, [bills]);
  const overdueCount = useMemo(() => bills.filter(bill => bill.due_status === 'OVERDUE').length, [bills]);

  const saveSchedule = async () => {
    if (!authToken || !name.trim()) {
      setError('Enter a name for this bill or expense.');
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(nextDueDate) || Number.isNaN(Date.parse(`${nextDueDate}T00:00:00`))) {
      setError('Enter the next due date in YYYY-MM-DD format.');
      return;
    }
    const amount = expectedAmount.trim() ? Number(expectedAmount) : undefined;
    if (amount !== undefined && (!Number.isFinite(amount) || amount <= 0)) {
      setError('Expected amount must be greater than zero, or leave it blank for a variable bill.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await createRecurringBill(authToken, {
        name: name.trim(), category, payee: payee.trim() || undefined,
        expected_amount_rupees: amount, frequency, next_due_date: nextDueDate,
        reminder_days_before: Math.max(0, Math.min(30, Number(reminderDays) || 0)),
      });
      setName(''); setPayee(''); setExpectedAmount(''); setNextDueDate(localToday());
      setFrequency('MONTHLY'); setReminderDays('3'); setShowForm(false);
      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const openRecordPayment = (bill: RecurringBill) => {
    setSelectedBill(bill);
    setPaidAmount(bill.expected_amount_rupees == null ? '' : String(bill.expected_amount_rupees));
  };

  const submitPaymentRecord = async () => {
    if (!authToken || !selectedBill) return;
    const amount = paidAmount.trim() ? Number(paidAmount) : undefined;
    if (amount !== undefined && (!Number.isFinite(amount) || amount <= 0)) {
      setError('Enter an amount greater than zero.');
      return;
    }
    if (selectedBill.expected_amount_rupees == null && amount == null) {
      setError('Enter the amount paid for this variable bill.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await recordBillPayment(authToken, selectedBill.id, {amount_rupees: amount});
      setSelectedBill(null);
      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const toggleSchedule = async (bill: RecurringBill) => {
    if (!authToken) return;
    setSaving(true);
    setError('');
    try {
      await updateRecurringBill(authToken, bill.id, {is_active: !bill.is_active});
      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const statusLabel = (status: RecurringBill['due_status']) => ({
    OVERDUE: t('billOverdue'), DUE_TODAY: t('billDueToday'), DUE_SOON: t('billDueSoon'),
    UPCOMING: t('billUpcoming'), PAUSED: t('billPaused'),
  }[status]);
  const dueDateLabel = (days: number) => days < 0
    ? t('billDaysOverdue').replace('{count}', String(Math.abs(days)))
    : days === 0 ? t('billDueToday') : t('billDaysLeft').replace('{count}', String(days));
  const statusColor = (status: RecurringBill['due_status']) => status === 'OVERDUE' ? '#B42318'
    : status === 'DUE_TODAY' || status === 'DUE_SOON' ? '#B54708' : teal;
  const formatMoney = (value?: number | null) => value == null ? t('billVariable') : `₹${Math.round(Number(value)).toLocaleString('en-IN')}`;

  return <Box flex={1} bg={surface} safeArea>
    <ScrollView px={5} pb={8} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
      <Box maxW={620} w="100%" alignSelf="center">
        <HStack alignItems="center" justifyContent="space-between" mt={3} mb={5}>
          <VStack flex={1}>
            <Text color={teal} fontSize="xs" bold letterSpacing="2">SAHAYAK AI</Text>
            <Text color={ink} fontSize="2xl" bold>{t('billSchedules')}</Text>
          </VStack>
          <Pressable onPress={() => navigation.navigate('UserMenu')} accessibilityRole="button" accessibilityLabel="Open profile" p={2}>
            <MaterialCommunityIcons name="account-circle-outline" size={29} color={teal}/>
          </Pressable>
        </HStack>

        <Text color={muted} mb={4}>{t('billScheduleSubtitle')}</Text>
        <HStack space={3} mb={4}>
          <SummaryCard label={t('billDueSoon')} value={String(dueSoonCount)} color="#B54708"/>
          <SummaryCard label={t('billOverdue')} value={String(overdueCount)} color={overdueCount ? '#B42318' : teal}/>
          <SummaryCard label={t('billSchedules')} value={String(bills.length)} color={ink}/>
        </HStack>

        <Alert status="info" mb={4} rounded="xl">
          <Alert.Icon/>
          <Text color={ink} fontSize="xs" flex={1}>{t('billManualOnly')}</Text>
        </Alert>
        {error ? <Alert status="error" mb={4} rounded="lg"><Alert.Icon/><Text flex={1}>{error}</Text></Alert> : null}

        <Button mb={4} bg={teal} onPress={() => {setShowForm(!showForm); setError('');}} _text={{color: 'white', bold: true}}>
          {showForm ? t('cancel') : `+ ${t('billAdd')}`}
        </Button>

        {showForm ? <Box bg="white" p={4} rounded="2xl" mb={5}>
          <Text color={ink} fontSize="lg" bold mb={3}>{t('billAdd')}</Text>
          <VStack space={3}>
            <Input value={name} onChangeText={setName} placeholder={t('billName')} bg="#FAFCFB" accessibilityLabel={t('billName')}/>
            <Select selectedValue={category} onValueChange={value => setCategory(value as BillCategory)} accessibilityLabel={t('billCategory')}>
              {categories.map(item => <Select.Item key={item.value} label={t(item.labelKey)} value={item.value}/>) }
            </Select>
            <Input value={payee} onChangeText={setPayee} placeholder={t('billPayee')} bg="#FAFCFB"/>
            <Input value={expectedAmount} onChangeText={setExpectedAmount} keyboardType="decimal-pad" placeholder={t('billExpectedAmount')} bg="#FAFCFB"/>
            <Text color={muted} fontSize="xs">{t('billVariableAmountHint')}</Text>
            <Select selectedValue={frequency} onValueChange={value => setFrequency(value as BillFrequency)} accessibilityLabel={t('billFrequency')}>
              {frequencies.map(item => <Select.Item key={item.value} label={t(item.labelKey)} value={item.value}/>) }
            </Select>
            <Input value={nextDueDate} onChangeText={setNextDueDate} placeholder={t('billNextDueDate')} bg="#FAFCFB" autoCapitalize="none"/>
            <Input value={reminderDays} onChangeText={setReminderDays} keyboardType="number-pad" placeholder={`${t('billReminderDays')} ${t('billDaysBefore')}`} bg="#FAFCFB"/>
            <Button bg={teal} isLoading={saving} onPress={saveSchedule} _text={{color: 'white', bold: true}}>{saving ? t('billSaving') : t('billSave')}</Button>
          </VStack>
        </Box> : null}

        <HStack justifyContent="space-between" alignItems="center" mb={3}>
          <Text color={ink} fontSize="lg" bold>{t('billSchedules')}</Text>
          <HStack space={2}>
            <Button size="sm" variant="outline" borderColor="#C9D8D5" onPress={() => setShowPaused(!showPaused)} _text={{color: muted}}>{showPaused ? t('billHidePaused') : t('billShowPaused')}</Button>
            <Button size="sm" variant="outline" borderColor="#C9D8D5" onPress={refresh} _text={{color: teal}}>{t('refresh')}</Button>
          </HStack>
        </HStack>
        {loading ? <ActivityIndicator color={teal} style={{marginVertical: 24}}/> : bills.length === 0 ? <Box bg="white" p={5} rounded="2xl" mb={5}>
          <Text color={ink} fontSize="lg" bold>{t('billNoSchedules')}</Text>
          <Text color={muted} mt={2}>{t('billScheduleSubtitle')}</Text>
        </Box> : <VStack space={3} mb={5}>
          {bills.map(bill => <Box key={bill.id} bg="white" p={4} rounded="xl">
            <HStack justifyContent="space-between" alignItems="flex-start">
              <VStack flex={1} pr={2}>
                <Text color={ink} bold fontSize="md">{bill.name}</Text>
                <Text color={muted} fontSize="xs">{t(categories.find(item => item.value === bill.category)?.labelKey || 'billOther')}{bill.payee ? ` · ${bill.payee}` : ''}</Text>
              </VStack>
              <Text color={statusColor(bill.due_status)} fontSize="xs" bold>{statusLabel(bill.due_status)}</Text>
            </HStack>
            <HStack justifyContent="space-between" mt={4}>
              <VStack><Text color={muted} fontSize="2xs">{t('billExpectedAmount')}</Text><Text color={ink} bold>{formatMoney(bill.expected_amount_rupees)}</Text></VStack>
              <VStack alignItems="flex-end"><Text color={muted} fontSize="2xs">{t('billNextDueDate')}</Text><Text color={ink} bold>{bill.next_due_date}</Text></VStack>
            </HStack>
            <Text color={muted} fontSize="xs" mt={2}>{t(frequencies.find(item => item.value === bill.frequency)?.labelKey || 'frequencyMonthly')} · {dueDateLabel(bill.days_until_due)}</Text>
            <HStack space={2} mt={3}>
              {bill.is_active ? <Button flex={1} minH={11} bg={teal} onPress={() => openRecordPayment(bill)} _text={{color: 'white', fontSize: 'xs', bold: true}}>{t('billMarkPaid')}</Button> : null}
              <Button flex={bill.is_active ? undefined : 1} minH={11} variant="outline" borderColor="#C9D8D5" onPress={() => toggleSchedule(bill)} isDisabled={saving} _text={{color: muted, fontSize: 'xs'}}>{bill.is_active ? t('billPauseSchedule') : t('billResumeSchedule')}</Button>
            </HStack>
          </Box>)}
        </VStack>}

        <Text color={ink} fontSize="lg" bold mb={3}>{t('billPaymentHistory')}</Text>
        {history.length === 0 ? <Box bg="white" p={4} rounded="xl"><Text color={muted}>{t('billNoHistory')}</Text></Box> : <VStack space={2} mb={5}>
          {history.slice(0, 10).map(item => <HStack key={item.id} bg="white" p={3} rounded="lg" justifyContent="space-between" alignItems="center">
            <VStack flex={1}><Text color={ink} bold>{item.bill_name}</Text><Text color={muted} fontSize="xs">{item.due_date} · {t('billRecordedPaid')}</Text></VStack>
            <Text color={teal} bold>{formatMoney(item.amount_rupees)}</Text>
          </HStack>)}
        </VStack>}
      </Box>
    </ScrollView>

    <Modal isOpen={Boolean(selectedBill)} onClose={() => setSelectedBill(null)}>
      <Modal.Content>
        <Modal.CloseButton/>
        <Modal.Header>{t('billMarkPaid')}</Modal.Header>
        <Modal.Body>
          <Text color={ink} bold mb={2}>{selectedBill?.name}</Text>
          <Text color={muted} fontSize="sm" mb={3}>{t('billManualOnly')}</Text>
          <Input value={paidAmount} onChangeText={setPaidAmount} keyboardType="decimal-pad" placeholder={t('billAmountPaid')}/>
        </Modal.Body>
        <Modal.Footer>
          <Button.Group space={2}>
            <Button variant="ghost" onPress={() => setSelectedBill(null)}>{t('cancel')}</Button>
            <Button bg={teal} isLoading={saving} onPress={submitPaymentRecord}>{t('confirm')}</Button>
          </Button.Group>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  </Box>;
}

function SummaryCard({label, value, color}: {label: string; value: string; color: string}) {
  return <Box flex={1} bg="white" p={3} rounded="xl">
    <Text color={muted} fontSize="2xs" bold>{label}</Text>
    <Text color={color} fontSize="xl" bold mt={1}>{value}</Text>
  </Box>;
}
