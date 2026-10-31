import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {Alert, Box, Button, Checkbox, HStack, Icon, Input, Pressable, Progress, ScrollView, Select, Text, VStack} from 'native-base';
import {MaterialCommunityIcons} from '@expo/vector-icons';
import {useFocusEffect, useNavigation} from '@react-navigation/native';
import {LoanJourney, loadJourney, saveJourney} from '../services/journeyStore';
import {useAuth} from '../contexts/AuthContext';
import {useLanguage} from '../contexts/LanguageContext';
import {apiErrorMessage} from '../services/apiClient';
import {calculateEmi, confirmDocument, createJourney, getJourney, getOffers, LenderOffer, recordConsent, reviseJourney, sendChatMessage, updateJourneyStage, uploadSyntheticDocument} from '../services/sahayakApi';

const ink = '#17343A';
const muted = '#61777B';
const teal = '#087F78';
const money = (value: number) => `₹${Math.round(value).toLocaleString('en-IN')}`;
const docTypes: Record<string, string> = {identity: 'PAN_CARD', income: 'SALARY_SLIP', bank: 'BANK_STATEMENT'};

const SahayakJourney = ({route}: any) => {
  const navigation = useNavigation<any>();
  const {logout, authToken, user} = useAuth();
  const {chatLanguage} = useLanguage();
  const [journey, setJourney] = useState<LoanJourney>();
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [reply, setReply] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState('');
  const [paymentOrderId, setPaymentOrderId] = useState<string | undefined>(route?.params?.paymentOrderId);
  const [paymentSummary, setPaymentSummary] = useState<any>();

  useEffect(() => {
    if (route?.params?.paymentOrderId) {
      setPaymentOrderId(String(route.params.paymentOrderId));
      setChatOpen(true);
      setMessage('Can you explain the status of this payment?');
    }
  }, [route?.params?.paymentOrderId]);

  useFocusEffect(useCallback(() => {
    let active = true;
    (async () => {
      if (!user) return;
      const local = await loadJourney(user.id);
      let next = local;
      if (local.backendJourneyId && authToken) {
        try {
          const remote = await getJourney(authToken, local.backendJourneyId);
          next = await saveJourney(user.id, {backendStage: remote.stage, estimatedEmi: Number(remote.calculation_summary?.estimated_emi_rupees) || local.estimatedEmi});
        } catch (e) {if (active) setError(apiErrorMessage(e));}
      }
      if (active) {setJourney(next); setLoading(false);}
    })();
    return () => {active = false;};
  }, [authToken, user]));

  const completedDocs = journey ? Object.values(journey.documents).filter(Boolean).length : 0;
  const progress = journey?.backendStage === 'READY_FOR_HANDOFF' ? 100 : Math.round((Number(Boolean(journey?.backendJourneyId)) + Number(Boolean(journey?.selectedOfferId)) + Number(Boolean(journey?.documentsPrepared)) + Number(journey?.status === 'submitted')) / 4 * 100);
  const askAssistant = async () => {
    if (!message.trim()) return;
    setChatBusy(true); setError('');
    try {
      const result = await sendChatMessage(authToken, {
        message: message.trim(), journey_id: journey?.backendJourneyId,
        language: chatLanguage,
        ...(paymentOrderId ? {payment_order_id: paymentOrderId, include_payment_context: true} : {}),
      });
      setReply(result.reply); setMessage('');
      setPaymentSummary(result.payment_context);
    } catch (e) {setError(apiErrorMessage(e));}
    finally {setChatBusy(false);}
  };

  if (loading || !journey) return <Box flex={1} bg="#F5F8F7" justifyContent="center" alignItems="center"><Text color={ink}>Loading your journey…</Text></Box>;
  return <Box flex={1} bg="#F5F8F7" safeArea>
    <ScrollView px={5} pb={8} showsVerticalScrollIndicator={false}>
      <Box maxW={560} w="100%" alignSelf="center">
        <HStack justifyContent="space-between" alignItems="center" mt={3} mb={6}>
          <VStack><Text color={teal} fontSize="xs" bold letterSpacing="2">SAHAYAK AI</Text><Text color={ink} fontSize="2xl" bold>Your financial journey</Text></VStack>
          <VStack space={2} alignItems="flex-end"><Button size="sm" variant="outline" borderColor="#C9D8D5" onPress={() => navigation.navigate('UserMenu')} _text={{color: ink}}>Profile</Button><Button size="xs" variant="ghost" onPress={logout} _text={{color: muted}}>Sign out</Button></VStack>
        </HStack>
        <Box bg={ink} p={5} rounded="2xl" mb={5}>
          <Text color="#A9DCD3" fontSize="xs" bold letterSpacing="1">PERSONAL LOAN READINESS</Text>
          <Text color="white" fontSize="xl" bold mt={2}>{journey.backendStage === 'READY_FOR_HANDOFF' ? 'Readiness review complete' : journey.backendJourneyId ? 'Your journey is in progress' : 'Start with what you need'}</Text>
          <Text color="#D4E3E1" mt={1}>{journey.backendStage === 'READY_FOR_HANDOFF' ? 'Demo handoff prepared. No lender has received an application.' : 'Your journey is saved with Sahayak. Loan decisions remain with lenders.'}</Text>
          <Progress value={progress} mt={4} bg="#476469" _filledTrack={{bg: '#65D6BB'}} />
          <Text color="#D4E3E1" fontSize="xs" mt={2}>{progress}% journey complete</Text>
          <Button mt={4} bg="#65D6BB" _text={{color: ink, bold: true}} onPress={() => navigation.navigate('LoanJourney')}>Continue journey</Button>
        </Box>
        <HStack space={3} mb={5}>
          <Box flex={1} bg="white" p={4} rounded="xl"><Text color={muted} fontSize="xs">BACKEND EMI</Text><Text color={ink} bold fontSize="lg">{journey.estimatedEmi ? `${money(journey.estimatedEmi)} / mo` : '—'}</Text><Text color={muted} fontSize="xs">Indicative synthetic offer</Text></Box>
          <Box flex={1} bg="white" p={4} rounded="xl"><Text color={muted} fontSize="xs">DEMO DOCUMENTS</Text><Text color={ink} bold fontSize="lg">{journey.documentsPrepared ? `${completedDocs}/3 checked` : 'Not prepared'}</Text><Text color={muted} fontSize="xs">Synthetic preflight only</Text></Box>
        </HStack>
        {error ? <Alert status="error" mb={4} rounded="lg"><Alert.Icon/><Text>{error}</Text></Alert> : null}
        <Text color={ink} fontSize="lg" bold mb={3}>Your next steps</Text>
        <VStack space={3} mb={5}>
          <StepCard title="1. Check loan readiness" detail="Enter an amount and compare a synthetic lender offer." done={Boolean(journey.backendJourneyId && journey.selectedOfferId)} onPress={() => navigation.navigate('LoanJourney')} />
          <StepCard title="2. Prepare demo documents" detail="Run the backend's synthetic OCR preflight. No real files are uploaded." done={Boolean(journey.documentsPrepared)} onPress={() => navigation.navigate('LoanJourney', {section: 'documents'})} />
          <StepCard title="3. Review your readiness" detail="Confirm consent and prepare a demo handoff state." done={journey.backendStage === 'READY_FOR_HANDOFF'} onPress={() => navigation.navigate('LoanJourney', {section: 'review'})} />
        </VStack>
        <Button
          bg={teal}
          _pressed={{bg: '#066B65'}}
          mb={3}
          onPress={() => navigation.navigate('ChatTab')}
          leftIcon={<Icon as={MaterialCommunityIcons} name="chat-processing-outline" size={5} color="white" />}
          _text={{color: 'white', bold: true}}>
          Open Sahayak AI Chat →
        </Button>
        <Button variant="outline" borderColor="#C9D8D5" mb={3} onPress={() => setChatOpen(!chatOpen)} _text={{color: ink}}>{chatOpen ? 'Close inline chat' : 'Quick inline question'}</Button>
        {chatOpen && <VStack space={3} mb={5}>
          {reply ? <Alert status="info" rounded="lg"><Alert.Icon/><Text color={ink}>{reply}</Text></Alert> : null}
          {paymentSummary ? <Text color={muted} fontSize="xs">Verified order {paymentSummary.order_id}: {paymentSummary.status}; wallet credit {paymentSummary.wallet_credit_recorded ? 'recorded' : 'not recorded'}.</Text> : null}
          <Input value={message} onChangeText={setMessage} placeholder="Ask about the loan journey" bg="white" />
          <Text color={muted} fontSize="xs">Messages go to the Sahayak API. Payment context uses your verified order and stays on this server unless separately consented and enabled.</Text>
          <Button bg={teal} isLoading={chatBusy} onPress={askAssistant}>Send message</Button>
        </VStack>}
        <Button variant="ghost" onPress={() => navigation.navigate('WalletTab')} _text={{color: teal}}>Open Ubanku wallet simulation</Button>
      </Box>
    </ScrollView>
  </Box>;
};

const StepCard = ({title, detail, done, onPress}: {title: string; detail: string; done: boolean; onPress: () => void}) => (
  <Pressable
    onPress={onPress}
    bg="white"
    p={4}
    rounded="xl"
    w="100%"
    _web={{cursor: 'pointer'}}
    _hover={{bg: '#F8FAFC', shadow: 2, transform: [{translateY: -2}]}}
    _pressed={{transform: [{scale: 0.98}]}}>
    <HStack justifyContent="space-between" alignItems="center" w="100%">
      <VStack flex={1} alignItems="flex-start" pr={3}>
        <Text color={ink} bold fontSize="md">{title}</Text>
        <Text color={muted} fontSize="sm" mt={0.5}>{detail}</Text>
      </VStack>
      <Text color={done ? teal : muted} bold fontSize="lg">{done ? 'Done' : '›'}</Text>
    </HStack>
  </Pressable>
);

export const LoanJourneyScreen = ({route}: any) => {
  const navigation = useNavigation<any>();
  const {authToken, user} = useAuth();
  const {currentLanguage, chatLanguage} = useLanguage();
  const [journey, setJourney] = useState<LoanJourney>();
  const [offers, setOffers] = useState<LenderOffer[]>([]);
  const [serverEmi, setServerEmi] = useState<any>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [assistant, setAssistant] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatReply, setChatReply] = useState('');
  const [chatBusy, setChatBusy] = useState(false);

  useEffect(() => {
    let active = true;
    if (!user) return;
    loadJourney(user.id).then(async local => {
      if (!active) return;
      const remote = local.backendJourneyId ? await getJourney(authToken, local.backendJourneyId).catch(() => null) : null;
      const next = {...local, ...(remote ? {backendStage: remote.stage, estimatedEmi: Number(remote.calculation_summary?.estimated_emi_rupees) || local.estimatedEmi} : {})};
      setJourney(next);
      await saveJourney(user.id, next);
    }).catch(e => {if (active) setError(apiErrorMessage(e));});
    return () => {active = false;};
  }, [authToken, user]);

  useEffect(() => {
    if (!journey || !authToken) return;
    let active = true;
    const timer = setTimeout(() => {
      getOffers(authToken, {
        loan_amount: Number(journey.amount) || undefined,
        tenure_months: journey.tenureMonths,
        monthly_income: Number(journey.monthlyIncome) || undefined,
      }).then(items => {
        if (active) setOffers(items);
      }).catch(e => {
        if (active) setError(apiErrorMessage(e));
      });
    }, 250);
    return () => {active = false; clearTimeout(timer);};
  }, [authToken, journey?.amount, journey?.tenureMonths, journey?.monthlyIncome]);

  const update = async (patch: Partial<LoanJourney>) => {
    if (!user) return;
    const next = await saveJourney(user.id, patch);
    setJourney(next);
  };
  const selectedOffer = useMemo(() => offers.find(offer => offer.offer_id === journey?.selectedOfferId) || offers[0], [offers, journey?.selectedOfferId]);

  useEffect(() => {
    if (!journey || !selectedOffer || Number(journey.amount) < 1000) {setServerEmi(undefined); return;}
    let active = true;
    const timer = setTimeout(() => {
      calculateEmi(authToken, {loan_amount: Number(journey.amount), tenure_months: journey.tenureMonths, offer_id: selectedOffer.offer_id}).then(result => {
        if (active) {setServerEmi(result); update({estimatedEmi: Number(result.estimated_emi_rupees), selectedOfferId: selectedOffer.offer_id, selectedOfferName: selectedOffer.lender_name});}
      }).catch(e => {if (active) setError(apiErrorMessage(e));});
    }, 350);
    return () => {active = false; clearTimeout(timer);};
  }, [authToken, journey?.amount, journey?.tenureMonths, selectedOffer?.offer_id]);

  if (!journey) return <Box flex={1} justifyContent="center" alignItems="center"><Text>Loading saved draft…</Text></Box>;
  const section = route?.params?.section || 'readiness';
  const field = (label: string, key: 'amount' | 'monthlyIncome' | 'existingEmi', placeholder: string) => <FormField label={label} value={journey[key]} placeholder={placeholder} onChangeText={(value: string) => update({[key]: value} as any)} keyboardType="numeric" testID={`journey-${key}`} />;
  const language = currentLanguage === 'hi' ? 'hi' : 'en';

  const saveReadiness = async () => {
    const amount = Number(journey.amount);
    if (!Number.isFinite(amount) || amount < 1000 || amount > 5000000) {setError('Enter a loan amount between ₹1,000 and ₹50,00,000.'); return;}
    if (!selectedOffer) {setError('No demo offers are available from the backend.'); return;}
    setBusy(true); setError('');
    try {
      const payload = {loan_amount: amount, preferred_tenure_months: journey.tenureMonths, purpose: 'Personal Loan', language};
      const remote = journey.backendJourneyId ? await reviseJourney(authToken, journey.backendJourneyId, payload) : await createJourney(authToken, payload);
      const progressed = remote.stage === 'INTENT_CAPTURED' ? await updateJourneyStage(authToken, remote.id, {stage: 'OFFERS_REVIEWED', customer_confirmed: false, selected_offer_id: selectedOffer.offer_id}) : remote;
      const calculation = await calculateEmi(authToken, {loan_amount: amount, tenure_months: journey.tenureMonths, offer_id: selectedOffer.offer_id});
      await update({backendJourneyId: remote.id, backendStage: progressed.stage, selectedOfferId: selectedOffer.offer_id, selectedOfferName: selectedOffer.lender_name, estimatedEmi: Number(calculation.estimated_emi_rupees), status: 'in_progress'});
      navigation.setParams({section: 'documents'});
    } catch (e) {setError(apiErrorMessage(e));}
    finally {setBusy(false);}
  };

  const prepareSyntheticDocuments = async () => {
    if (!journey.backendJourneyId) {setError('Save the readiness step first.'); return;}
    const selected = Object.entries(journey.documents).filter(([, checked]) => checked).map(([key]) => key);
    if (!selected.length) {setError('Select at least one document type for the synthetic preflight.'); return;}
    setBusy(true); setError('');
    try {
      await recordConsent(authToken, journey.backendJourneyId, {scope: 'document_ocr_processing', purpose: 'User requested synthetic demo OCR preflight; no real document file or personal document content is uploaded.', is_granted: true});
      const ids = [...(journey.remoteDocumentIds || [])];
      for (const key of selected) {
        const result = await uploadSyntheticDocument(authToken, journey.backendJourneyId, docTypes[key]);
        const fields = Object.fromEntries(Object.entries(result.fields || {}).map(([name, value]: [string, any]) => [name, String(value.raw_value || '')]));
        await confirmDocument(authToken, journey.backendJourneyId, result.document_id, fields);
        ids.push(result.document_id);
      }
      const remote = await updateJourneyStage(authToken, journey.backendJourneyId, {stage: 'DOCUMENTS_CONFIRMED', customer_confirmed: true});
      await update({remoteDocumentIds: ids, documentsPrepared: true, backendStage: remote.stage, status: 'ready_to_review'});
      navigation.setParams({section: 'review'});
    } catch (e) {setError(apiErrorMessage(e));}
    finally {setBusy(false);}
  };

  const prepareHandoff = async () => {
    if (!journey.backendJourneyId || journey.backendStage !== 'DOCUMENTS_CONFIRMED') {setError('Complete the backend document preflight before final review.'); return;}
    if (!journey.consentToPrepare) {setError('Confirm the demo handoff consent first.'); return;}
    setBusy(true); setError('');
    try {
      await recordConsent(authToken, journey.backendJourneyId, {scope: 'application_handoff', purpose: 'User confirms the synthetic demo readiness record may advance to READY_FOR_HANDOFF; no lender is contacted.', is_granted: true});
      const remote = await updateJourneyStage(authToken, journey.backendJourneyId, {stage: 'READY_FOR_HANDOFF', customer_confirmed: true});
      await update({status: 'submitted', submittedAt: new Date().toISOString(), backendStage: remote.stage});
    } catch (e) {setError(apiErrorMessage(e));}
    finally {setBusy(false);}
  };

  const askJourneyAssistant = async () => {
    if (!chatMessage.trim()) return;
    setChatBusy(true); setError('');
    try {
      const result = await sendChatMessage(authToken, {message: chatMessage.trim(), journey_id: journey.backendJourneyId, language: chatLanguage});
      setChatReply(result.reply); setChatMessage('');
    } catch (e) {setError(apiErrorMessage(e));}
    finally {setChatBusy(false);}
  };

  return <Box flex={1} safeArea bg="#F5F8F7"><ScrollView px={5} showsVerticalScrollIndicator={false}>
    <Box maxW={560} w="100%" alignSelf="center">
      <Button variant="ghost" alignSelf="flex-start" onPress={() => navigation.goBack()} _text={{color: teal}}>‹ Back</Button>
      <Text color={teal} fontSize="xs" bold letterSpacing="1" mt={2}>PERSONAL LOAN JOURNEY</Text>
      <Text color={ink} fontSize="2xl" bold mb={2}>{section === 'documents' ? 'Synthetic document preflight' : section === 'review' ? 'Review your readiness' : 'Let’s understand your goal'}</Text>
      <Text color={muted} mb={5}>Journey state and calculations come from the Sahayak backend. No real lender application is submitted.</Text>
      {error ? <Alert status="error" mb={4} rounded="lg"><Alert.Icon/><Text>{error}</Text></Alert> : null}
      {section === 'readiness' && <VStack space={4}>
        {field('How much would you like to plan for?', 'amount', 'e.g. 200000')}
        {field('Monthly take-home income (saved on this device)', 'monthlyIncome', 'e.g. 45000')}
        <Box><Text color={ink} bold mb={1}>Employment (saved on this device)</Text><Select selectedValue={journey.employment} placeholder="Select work situation" bg="white" onValueChange={employment => update({employment})}><Select.Item label="Salaried" value="salaried"/><Select.Item label="Self-employed" value="self_employed"/><Select.Item label="Other / exploring" value="other"/></Select></Box>
        {field('Existing monthly loan payments (optional)', 'existingEmi', '0')}
        <Box><Text color={ink} bold mb={1}>Indicative loan product</Text><Select testID="offer-select" selectedValue={selectedOffer?.offer_id} placeholder="Select a product" bg="white" onValueChange={offerId => update({selectedOfferId: offerId})}>{offers.map(offer => <Select.Item key={offer.offer_id} label={`${offer.lender_name} · ${offer.annual_interest_rate_percent}%`} value={offer.offer_id}/>)}</Select><Text color={muted} fontSize="xs" mt={1}>{selectedOffer?.source_type === 'synthetic' ? 'Synthetic demo terms; this is not a lender offer or approval.' : `Source: ${selectedOffer?.source_name || 'partner catalogue'}${selectedOffer?.last_verified_at ? ` · checked ${new Date(selectedOffer.last_verified_at).toLocaleDateString()}` : ''}`}</Text>{selectedOffer?.eligibility_data_missing ? <Text color={muted} fontSize="xs" mt={1}>Eligibility details still needed: {selectedOffer.missing_criteria?.join(', ')}.</Text> : null}</Box>
        <Box bg="white" p={4} rounded="xl"><Text color={ink} bold>Backend EMI estimate</Text><Text color={teal} fontSize="2xl" bold mt={2}>{serverEmi ? `${money(Number(serverEmi.estimated_emi_rupees))} / month` : journey.estimatedEmi ? `${money(journey.estimatedEmi)} / month` : 'Enter an eligible amount'}</Text><Text color={muted} fontSize="sm">{serverEmi ? `${serverEmi.annual_interest_rate_percent}% annual interest · ${serverEmi.tenure_months} months` : 'The server calculates the offer using deterministic decimal arithmetic.'}</Text><Select mt={3} selectedValue={String(journey.tenureMonths)} onValueChange={v => update({tenureMonths: Number(v)})} bg="#F5F8F7"><Select.Item label="12 months" value="12"/><Select.Item label="24 months" value="24"/><Select.Item label="36 months" value="36"/><Select.Item label="48 months" value="48"/></Select></Box>
        <Button testID="journey-save" bg={teal} isLoading={busy} onPress={saveReadiness}>Save and continue</Button>
      </VStack>}
      {section === 'documents' && <VStack space={3}>
        <Alert status="warning" rounded="lg"><Alert.Icon/><Text color={ink}>Demo only: the backend generates synthetic OCR values. This sends no files and must not be treated as document verification.</Text></Alert>
        <DocToggle label="Synthetic identity record (PAN)" value={journey.documents.identity} onChange={(v: boolean) => update({documents: {...journey.documents, identity: v}})}/>
        <DocToggle label="Synthetic income record (salary slip)" value={journey.documents.income} onChange={(v: boolean) => update({documents: {...journey.documents, income: v}})}/>
        <DocToggle label="Synthetic bank statement record" value={journey.documents.bank} onChange={(v: boolean) => update({documents: {...journey.documents, bank: v}})}/>
        <Button testID="journey-documents" bg={teal} mt={3} isLoading={busy} onPress={prepareSyntheticDocuments}>Consent and run synthetic preflight</Button>
      </VStack>}
      {section === 'review' && <VStack space={4}>
        <Box bg="white" p={4} rounded="xl"><ReviewLine label="Requested amount" value={journey.amount ? money(Number(journey.amount)) : 'Not provided'}/><ReviewLine label="Offer" value={journey.selectedOfferName || selectedOffer?.lender_name || 'Not selected'}/><ReviewLine label="Backend EMI" value={journey.estimatedEmi ? `${money(journey.estimatedEmi)} / month` : 'Not available'}/><ReviewLine label="Backend stage" value={journey.backendStage || 'Not created'}/><ReviewLine label="Synthetic records" value={String(journey.remoteDocumentIds?.length || 0)}/></Box>
        <Checkbox testID="handoff-consent" value="consent" isChecked={journey.consentToPrepare} onChange={v => update({consentToPrepare: v})} _text={{color: ink}}>I agree to move this synthetic demo record to readiness handoff. No lender will receive an application.</Checkbox>
        {journey.backendStage === 'READY_FOR_HANDOFF' && <Alert status="success" rounded="xl"><Alert.Icon/><Text color={ink}>Backend readiness handoff is prepared. This is not a submitted lender application.</Text></Alert>}
        <Button testID="journey-handoff" bg={teal} isLoading={busy} isDisabled={journey.backendStage === 'READY_FOR_HANDOFF'} onPress={prepareHandoff}>Prepare demo handoff</Button>
        <Button variant="outline" borderColor="#C9D8D5" onPress={() => navigation.setParams({section: 'readiness'})} _text={{color: ink}}>Edit answers</Button>
      </VStack>}
      <Button mt={6} variant="ghost" onPress={() => setAssistant(!assistant)} _text={{color: teal}}>{assistant ? 'Close backend chat' : 'Ask Sahayak'}</Button>
      {assistant && <VStack space={3} mb={8}>
        {chatReply ? <Alert status="info" rounded="lg"><Alert.Icon/><Text color={ink}>{chatReply}</Text></Alert> : null}
        <Input value={chatMessage} onChangeText={setChatMessage} placeholder="Ask about this journey" bg="white" />
        <Text color={muted} fontSize="xs">External AI processing stays off; answers may use the backend's deterministic fallback.</Text>
        <Button bg={teal} isLoading={chatBusy} onPress={askJourneyAssistant}>Send</Button>
      </VStack>}
      <Button mt={4} mb={8} variant="ghost" onPress={() => navigation.navigate('UserMenu')} _text={{color: muted}}>Language and profile settings</Button>
    </Box>
  </ScrollView></Box>;
};

const FormField = ({label, value, placeholder, onChangeText, keyboardType, testID}: any) => <Box><Text color={ink} bold mb={1}>{label}</Text><Input testID={testID} value={value} placeholder={placeholder} onChangeText={onChangeText} keyboardType={keyboardType} bg="white" borderColor="#D5E0DE" rounded="lg"/></Box>;
const DocToggle = ({label, value, onChange}: any) => <Checkbox value={label} isChecked={value} onChange={onChange} bg="white" p={4} rounded="xl" _text={{color: ink, flex: 1}}>{label}</Checkbox>;
const ReviewLine = ({label, value}: any) => <HStack justifyContent="space-between" py={2} borderBottomWidth={1} borderColor="#E8EFED"><Text color={muted}>{label}</Text><Text color={ink} bold>{value}</Text></HStack>;

export default SahayakJourney;
