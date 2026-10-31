import React from 'react';
import {View, Text, Input, Button, VStack} from 'native-base';
import useUserForm from '../../../../hooks/Auth/useUserForm';

type CreditDebitCardFormProps = {
  onSubmit: (data: {
    cardNumber: string;
    cardholderName: string;
    expirationDate: string;
    cvv: string;
  }) => void;
};

const UCreditDebitCardForm: React.FC<CreditDebitCardFormProps> = ({
  onSubmit,
}) => {
  const cardNumberInput = useUserForm('', value => {
    if (value.length !== 16)
      return 'Card number must be 16 digits';
    return '';
  });
  const cardholderNameInput = useUserForm('', value => {
    if (value.length === 0) return 'Cardholder name is required';
    return '';
  });
  const expirationDateInput = useUserForm('', value => {
    if (!/^\d{2}\/\d{2}$/.test(value))
      return 'Expiry date must be in MM/YY format';
    return '';
  });
  const cvvInput = useUserForm('', value => {
    if (value.length !== 3) return 'CVV must be 3 digits';
    return '';
  });

  const handleSubmit = () => {
    if (
      cardNumberInput.validate() &&
      cardholderNameInput.validate() &&
      expirationDateInput.validate() &&
      cvvInput.validate()
    ) {
      onSubmit({
        cardNumber: cardNumberInput.value,
        cardholderName: cardholderNameInput.value,
        expirationDate: expirationDateInput.value,
        cvv: cvvInput.value,
      });
    }
  };

  return (
    <VStack space={3} mt={3}>
      <Input
        placeholder="Card Number"
        keyboardType="numeric"
        maxLength={16}
        value={cardNumberInput.value}
        onChangeText={cardNumberInput.onChange}
      />
      {cardNumberInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {cardNumberInput.error}
        </Text>
      )}
      <Input
        placeholder="Cardholder Name"
        value={cardholderNameInput.value}
        onChangeText={cardholderNameInput.onChange}
      />
      {cardholderNameInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {cardholderNameInput.error}
        </Text>
      )}
      <Input
        placeholder="Expiry Date (MM/YY)"
        maxLength={5}
        value={expirationDateInput.value}
        onChangeText={expirationDateInput.onChange}
      />
      {expirationDateInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {expirationDateInput.error}
        </Text>
      )}
      <Input
        placeholder="CVV"
        keyboardType="numeric"
        maxLength={3}
        value={cvvInput.value}
        onChangeText={cvvInput.onChange}
      />
      {cvvInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {cvvInput.error}
        </Text>
      )}
      <Button mt={2} onPress={handleSubmit}>Submit</Button>
    </VStack>
  );
};

export default UCreditDebitCardForm;
