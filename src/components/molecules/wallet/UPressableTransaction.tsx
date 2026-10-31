import React from 'react';
import {Pressable, HStack, VStack, Text, Box, Center} from 'native-base';
import iTransaction from '../../../interfaces/Wallet/iTransaction';
import {formatRupees} from '../../../utils/currency';
import IconsTypesTransaction from '../../../utils/wallet/IconsTypesTransaction';

interface UPressableTransactionProps {
  transaction: iTransaction;
  onPress?: () => void;
}

const UPressableTransaction: React.FC<UPressableTransactionProps> = ({
  transaction,
  onPress = null,
}) => {
  const {transactionType, transactionDate, transactionName, transactionValue} =
    transaction;

  const formattedDate = new Date(transactionDate).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  const formattedValue = formatRupees(transactionValue);

  return (
    <Pressable
      onPress={onPress}
      _web={{cursor: 'pointer'}}
      _hover={{bg: 'gray.50'}}
      rounded="lg"
      px={2}
      py={2}
      mx={-2}>
      {({isPressed}) => (
        <HStack
          alignItems="center"
          space={4}
          style={{
            transform: [{scale: isPressed ? 0.98 : 1}],
          }}>
          <Center>
            <IconsTypesTransaction transactionType={transactionType} />
          </Center>
          <VStack space={1} width="60%">
            <Text color="text.600" fontSize={10} fontWeight={400}>
              {formattedDate}
            </Text>
            <Text color="text.800" fontSize={14} fontWeight={400} isTruncated>
              {transactionName}
            </Text>
          </VStack>
          <Box flex={1}>
            <Text
              textAlign="right"
              fontWeight={600}
              color={transactionValue >= 0 ? 'success.700' : 'error.600'}>
              {transactionValue >= 0 ? '+ ' : '- '}₹ {formattedValue}
            </Text>
          </Box>
        </HStack>
      )}
    </Pressable>
  );
};

export default UPressableTransaction;
