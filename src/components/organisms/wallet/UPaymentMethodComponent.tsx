import React, {useRef, useState} from 'react';
import {
  View,
  Radio,
  Button,
  Checkbox,
  Modal,
  HStack,
} from 'native-base';
import {Animated, StyleSheet} from 'react-native';
import UNequiForm from '../../molecules/wallet/PaymentMethodForms/UNequiForm';
import UCreditDebitCardForm from '../../molecules/wallet/PaymentMethodForms/UCreditDebitCardForm';
import {KeyboardAwareScrollView} from 'react-native-keyboard-aware-scroll-view';
import UBasicWrapperNoSafeArea from '../../molecules/UBasicWrapperNoSafeArea';
import UBasicCard from '../../atoms/UBasicCard';
import ULine from '../../atoms/ULine';
import UText from '../../atoms/UText';
import {SafeAreaView} from 'react-native-safe-area-context';
import UTextWithLinks from '../../atoms/UTextWithLinks';
import {useLanguage} from '../../../contexts/LanguageContext';

type PaymentMethod = {
  type: 'UPI' | 'Nequi' | 'Daviplata' | 'CreditCard' | 'DebitCard' | 'DebitCreditCard';
  number: string;
};

type Props = {
  paymentMethods: PaymentMethod[];
  onAddPaymentMethod?: (paymentMethod: PaymentMethod) => void;
};

const UPaymentMethodComponent: React.FC<Props> = ({
  paymentMethods = [],
  onAddPaymentMethod = () => {},
}) => {
  const {t} = useLanguage();
  const [selectedPaymentMethodValue, setSelectedPaymentMethodValue] = useState(
    paymentMethods.length > 0 ? paymentMethods[0].number : '',
  );
  const [showModal, setShowModal] = useState(false);
  const [selectedNewPaymentMethodType, setSelectedNewPaymentMethodType] =
    useState<
      | 'CreditCard'
      | 'DebitCard'
      | 'Nequi'
      | 'UPI'
      | 'Daviplata'
      | 'DebitCreditCard'
      | undefined
    >(undefined);

  const [acceptTermsAndConditions, setAcceptTermsAndConditions] =
    useState(false);

  const upiFormRef = useRef<{submit: () => void}>(null);
  const creditDebitCardFormRef = useRef<{submit: () => void}>(null);

  const handleAddUpiPaymentMethod = (data: {
    cellphone: string;
    firstName: string;
    lastName: string;
    documentType: string;
    documentNumber: string;
  }) => {
    onAddPaymentMethod({type: 'UPI', number: data.cellphone});
    setShowModal(false);
  };

  const handleAddCreditDebitCardPaymentMethod = (data: {
    cardNumber: string;
    cardholderName: string;
    expirationDate: string;
    cvv: string;
  }) => {
    onAddPaymentMethod({
      type: (selectedNewPaymentMethodType as any) || 'DebitCreditCard',
      number: data.cardNumber.slice(-4),
    });
    setShowModal(false);
  };

  const handleAddPaymentMethod = () => {
    if (selectedNewPaymentMethodType === 'UPI' || selectedNewPaymentMethodType === 'Nequi') {
      upiFormRef.current?.submit();
    } else if (
      selectedNewPaymentMethodType === 'DebitCreditCard' ||
      selectedNewPaymentMethodType === 'DebitCard' ||
      selectedNewPaymentMethodType === 'CreditCard'
    ) {
      creditDebitCardFormRef.current?.submit();
    }
  };

  const [formAnimation] = React.useState(new Animated.Value(0));
  const animateForm = () => {
    Animated.timing(formAnimation, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  return (
    <View>
      {paymentMethods.length > 0 && (
        <Radio.Group
          mb={4}
          name="payment-method"
          value={selectedPaymentMethodValue}
          onChange={setSelectedPaymentMethodValue}>
          {paymentMethods.map(paymentMethod => (
            <Radio value={paymentMethod.number} key={paymentMethod.number} my={1}>
              {`${paymentMethod.type} - ${paymentMethod.number}`}
            </Radio>
          ))}
        </Radio.Group>
      )}

      <Button variant="subtle" onPress={() => setShowModal(true)}>
        {t('addPaymentMethod')}
      </Button>
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        animationPreset="slide"
        _backdrop={{
          _dark: {
            bg: 'coolGray.800',
          },
          bg: 'white',
        }}>
        <SafeAreaView style={styles.modalContent}>
          <KeyboardAwareScrollView style={{flex: 1}}>
            <UBasicWrapperNoSafeArea
              style={styles.modalContent}
              onPressCloseButton={() => setShowModal(false)}
              onPressButton={handleAddPaymentMethod}
              buttonTitle={t('linkAccount')}
              hideButton={!selectedNewPaymentMethodType}
              hideAdditionalComponent={!selectedNewPaymentMethodType}
              additionalComponent={
                <HStack alignItems={'center'} space={2}>
                  <Checkbox
                    aria-label="accept terms and conditions"
                    value="agree"
                    isChecked={acceptTermsAndConditions}
                    onChange={isChecked =>
                      setAcceptTermsAndConditions(isChecked)
                    }
                  />
                  <UTextWithLinks
                    firstText="I agree that I have read the"
                    secondText="terms and conditions"
                    secondLink="https://google.com/terms"
                    thirdText="and the"
                    fourthText="privacy policy"
                    fourthLink="https://google.com/privacy"
                    fifthText="to complete this action"
                  />
                </HStack>
              }
              isDisabled={!acceptTermsAndConditions}>
              <UText title center weight={500}>
                {t('paymentMethods')}
              </UText>
              <UBasicCard>
                <Radio.Group
                  space={3}
                  name="new-payment-method-type"
                  defaultValue={selectedNewPaymentMethodType}
                  onChange={(nextValue: any) => {
                    setSelectedNewPaymentMethodType(nextValue);
                    formAnimation.setValue(0);
                    animateForm();
                  }}>
                  <Radio size={'sm'} value="DebitCreditCard">
                    Credit / Debit Card
                  </Radio>
                  <ULine />
                  <Radio size={'sm'} value="UPI">
                    UPI / Mobile Banking
                  </Radio>
                </Radio.Group>
              </UBasicCard>

              <Animated.View
                style={{
                  transform: [
                    {
                      translateY: formAnimation.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-30, 0],
                      }),
                    },
                  ],
                  opacity: formAnimation,
                }}>
                {(selectedNewPaymentMethodType === 'UPI' || selectedNewPaymentMethodType === 'Nequi') && (
                  <UNequiForm
                    ref={upiFormRef}
                    onSubmit={handleAddUpiPaymentMethod}
                  />
                )}
                {(selectedNewPaymentMethodType === 'DebitCreditCard' ||
                  selectedNewPaymentMethodType === 'CreditCard' ||
                  selectedNewPaymentMethodType === 'DebitCard') && (
                  <UCreditDebitCardForm
                    onSubmit={handleAddCreditDebitCardPaymentMethod}
                  />
                )}
              </Animated.View>
            </UBasicWrapperNoSafeArea>
          </KeyboardAwareScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 0,
    minHeight: '100%',
  },
});

export default UPaymentMethodComponent;
