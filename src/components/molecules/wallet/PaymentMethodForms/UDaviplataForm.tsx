import React from 'react';
import {Text, Input, Select, Button, CheckIcon, VStack} from 'native-base';
import useUserForm from '../../../../hooks/Auth/useUserForm';

type DaviplataProps = {
  onSubmit: (data: {
    cellphone: string;
    firstName: string;
    lastName: string;
    documentType: string;
    documentNumber: string;
  }) => void;
};

const UDaviplataForm: React.FC<DaviplataProps> = ({onSubmit}) => {
  const cellphoneInput = useUserForm('', value => {
    if (value.length < 10)
      return 'Mobile number must have at least 10 digits';
    return '';
  });
  const firstNameInput = useUserForm('', value => {
    if (value.length === 0) return 'First name is required';
    return '';
  });
  const lastNameInput = useUserForm('', value => {
    if (value.length === 0) return 'Last name is required';
    return '';
  });
  const documentTypeInput = useUserForm('aadhaar', () => '');
  const documentNumberInput = useUserForm('', value => {
    if (value.length === 0) return 'Document number is required';
    return '';
  });

  const handleSubmit = () => {
    if (
      cellphoneInput.validate() &&
      firstNameInput.validate() &&
      lastNameInput.validate() &&
      documentNumberInput.validate()
    ) {
      onSubmit({
        cellphone: cellphoneInput.value,
        firstName: firstNameInput.value,
        lastName: lastNameInput.value,
        documentType: documentTypeInput.value,
        documentNumber: documentNumberInput.value,
      });
    }
  };

  return (
    <VStack space={3} mt={3}>
      <Input
        placeholder="Mobile Number"
        keyboardType="phone-pad"
        value={cellphoneInput.value}
        onChangeText={cellphoneInput.onChange}
      />
      {cellphoneInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {cellphoneInput.error}
        </Text>
      )}
      <Input
        placeholder="First Name"
        value={firstNameInput.value}
        onChangeText={firstNameInput.onChange}
      />
      {firstNameInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {firstNameInput.error}
        </Text>
      )}
      <Input
        placeholder="Last Name"
        value={lastNameInput.value}
        onChangeText={lastNameInput.onChange}
      />
      {lastNameInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {lastNameInput.error}
        </Text>
      )}
      <Select
        selectedValue={documentTypeInput.value}
        onValueChange={itemValue => documentTypeInput.onChange(itemValue)}
        _selectedItem={{
          bg: 'cyan.600',
          endIcon: <CheckIcon size={4} />,
        }}>
        <Select.Item label="Aadhaar Card" value="aadhaar" />
        <Select.Item label="PAN Card" value="pan" />
        <Select.Item label="Passport" value="passport" />
      </Select>
      <Input
        placeholder="Document Number"
        value={documentNumberInput.value}
        onChangeText={documentNumberInput.onChange}
      />
      {documentNumberInput.error !== '' && (
        <Text color="error.600" fontSize="xs">
          {documentNumberInput.error}
        </Text>
      )}
      <Button mt={2} onPress={handleSubmit}>Submit</Button>
    </VStack>
  );
};

export default UDaviplataForm;
