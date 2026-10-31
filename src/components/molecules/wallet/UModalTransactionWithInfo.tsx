import React from 'react';
import {View} from 'react-native';
import {Button, Center, HStack, Modal, Text, VStack} from 'native-base';
import {PanGestureHandler, State} from 'react-native-gesture-handler';
import IconsTypesTransaction from '../../../utils/wallet/IconsTypesTransaction';
import USpacedTexts from '../../atoms/USpacedTexts';
import {formatRupees} from '../../../utils/currency';
import UTwoButtonts from '../../atoms/UTwoButtonts';
import {useLanguage} from '../../../contexts/LanguageContext';
import {useNavigation} from '@react-navigation/native';

interface TransactionModalProps {
  visible: boolean;
  onClose: () => void;
  transactionName: string;
  transactionType: string;
  transactionStatus: string;
  transactionDate: string;
  transactionId: string;
  transactionPaymentMethod: string;
  transactionValue: number;
}

const UModalTransactionWithInfo: React.FC<TransactionModalProps> = ({
  visible,
  onClose,
  transactionName,
  transactionType,
  transactionStatus,
  transactionDate,
  transactionId,
  transactionPaymentMethod,
  transactionValue,
}) => {
  const {t} = useLanguage();
  const navigation = useNavigation<any>();

  const onGestureEvent = ({nativeEvent}: any) => {
    if (
      nativeEvent.oldState === State.ACTIVE &&
      nativeEvent.translationY > 30
    ) {
      onClose();
    }
  };

  const date = new Date(transactionDate);
  const formattedDate = `${date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })} - ${date.toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: 'numeric',
    hour12: true,
  })}`;

  const formattedValue = formatRupees(transactionValue);

  return (
    <Modal isOpen={visible} onClose={onClose}>
      <PanGestureHandler onHandlerStateChange={onGestureEvent}>
        <View style={{flex: 1, width: '100%'}}>
          <View style={{flex: 1}} />
          <View
            style={{
              backgroundColor: 'white',
              borderTopLeftRadius: 20,
              borderTopRightRadius: 20,
              padding: 20,
              paddingVertical: 33,
            }}>
            <View
              style={{
                width: 40,
                height: 5,
                backgroundColor: '#ccc',
                alignSelf: 'center',
                marginBottom: 20,
                borderRadius: 5,
              }}
            />
            <HStack alignItems="center" space={4}>
              <Center>
                <IconsTypesTransaction
                  size="md"
                  transactionType={transactionType}
                />
              </Center>
              <VStack space={1} width="80%">
                <Text
                  color="text.800"
                  fontSize={20}
                  fontWeight={700}
                  isTruncated>
                  {transactionName}
                </Text>
                <Text color="text.700" fontSize={14} fontWeight={400}>
                  {formattedDate}
                </Text>
              </VStack>
            </HStack>
            <VStack space={2} my={7}>
              <USpacedTexts
                textLeft={t('status')}
                weightLeft={500}
                colorLeft="text.700"
                textRight={transactionStatus}
                weightRight={400}
                colorRight="text.900"
                fzRight={14}
              />
              <USpacedTexts
                weightLeft={500}
                colorLeft="text.700"
                textLeft={t('transactionNum')}
                textRight={transactionId}
                weightRight={400}
                colorRight="text.900"
                fzRight={14}
              />
              <USpacedTexts
                weightLeft={500}
                colorLeft="text.700"
                textLeft={t('paymentMethod')}
                textRight={transactionPaymentMethod}
                weightRight={400}
                colorRight="text.900"
                fzRight={14}
              />
              <USpacedTexts
                weightLeft={500}
                colorLeft="text.700"
                textLeft={t('amount')}
                textRight={`${
                  transactionValue >= 0 ? '+ ' : '- '
                }₹ ${formattedValue}`}
                colorRight={transactionValue >= 0 ? 'success.700' : 'error.600'}
                weightRight={500}
                fzRight={16}
              />
            </VStack>
            <UTwoButtonts
              onPressFirstButton={onClose}
              firstButtonTitle={t('done')}
              secondButtonTitle={t('transactionHelp')}
              onPressSecondButton={() => {
                onClose();
                navigation.navigate('ChatTab', {paymentOrderId: transactionId});
              }}
            />
          </View>
        </View>
      </PanGestureHandler>
    </Modal>
  );
};

export default UModalTransactionWithInfo;
