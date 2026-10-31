import React, {forwardRef, useImperativeHandle, useRef} from 'react';
import {
  Input,
  Select,
  Button,
  CheckIcon,
  FormControl,
  HStack,
} from 'native-base';
import useUserForm from '../../../../hooks/Auth/useUserForm';
import UText from '../../../atoms/UText';
import {TextInput} from 'react-native';
import UBasicCard from '../../../atoms/UBasicCard';

type NequiFormProps = {
  onSubmit: (data: {
    cellphone: string;
    firstName: string;
    lastName: string;
    documentType: string;
    documentNumber: string;
  }) => void;
  showSubmitButton?: boolean;
};

export type NequiFormHandles = {submit: () => void};

const UNequiForm = forwardRef<NequiFormHandles, NequiFormProps>(
  ({onSubmit, showSubmitButton}, ref) => {
    const cellphoneInput = useUserForm('', value => {
      if (value.length < 10)
        return 'Phone number must have at least 10 digits';
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

    const firstNameInputRef = useRef<TextInput>(null);
    const lastNameInputRef = useRef<TextInput>(null);
    const documentNumberInputRef = useRef<TextInput>(null);
    const documentTypeInputRef = useRef<TextInput>(null);

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

    useImperativeHandle(ref, () => ({
      submit: handleSubmit,
    }));

    return (
      <UBasicCard>
        <FormControl isInvalid={cellphoneInput.error !== ''}>
          <FormControl.Label>
            <UText size={12} weight={500} color="text.600">
              Mobile Number
            </UText>
          </FormControl.Label>
          <Input
            placeholder="9876543210"
            keyboardType="phone-pad"
            value={cellphoneInput.value}
            onChangeText={cellphoneInput.onChange}
            returnKeyType="next"
            onSubmitEditing={() => firstNameInputRef.current?.focus()}
          />
          <FormControl.ErrorMessage>
            {cellphoneInput.error}
          </FormControl.ErrorMessage>
        </FormControl>
        <HStack space={2} mt={2}>
          <FormControl isInvalid={firstNameInput.error !== ''} flex={0.5}>
            <FormControl.Label>
              <UText size={12} weight={500} color="text.600">
                First Name
              </UText>
            </FormControl.Label>
            <Input
              placeholder="Andy"
              value={firstNameInput.value}
              onChangeText={firstNameInput.onChange}
              ref={firstNameInputRef}
              returnKeyType="next"
              onSubmitEditing={() => lastNameInputRef.current?.focus()}
            />
            <FormControl.ErrorMessage>
              {firstNameInput.error}
            </FormControl.ErrorMessage>
          </FormControl>
          <FormControl isInvalid={lastNameInput.error !== ''} flex={0.5}>
            <FormControl.Label>
              <UText size={12} weight={500} color="text.600">
                Last Name
              </UText>
            </FormControl.Label>
            <Input
              placeholder="Sharma"
              value={lastNameInput.value}
              onChangeText={lastNameInput.onChange}
              ref={lastNameInputRef}
              returnKeyType="next"
              onSubmitEditing={() => documentTypeInputRef.current?.focus()}
            />
            <FormControl.ErrorMessage>
              {lastNameInput.error}
            </FormControl.ErrorMessage>
          </FormControl>
        </HStack>

        <FormControl isInvalid={documentTypeInput.error !== ''} mt={2}>
          <FormControl.Label>
            <UText size={12} weight={500} color="text.600">
              Document Type
            </UText>
          </FormControl.Label>

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
            <Select.Item label="Voter ID" value="voter_id" />
          </Select>
          <FormControl.ErrorMessage>
            {documentTypeInput.error}
          </FormControl.ErrorMessage>
        </FormControl>

        <FormControl isInvalid={documentNumberInput.error !== ''} mt={2}>
          <FormControl.Label>
            <UText size={12} weight={500} color="text.600">
              Document Number
            </UText>
          </FormControl.Label>
          <Input
            placeholder="Enter ID number"
            value={documentNumberInput.value}
            onChangeText={documentNumberInput.onChange}
            ref={documentNumberInputRef}
          />

          <FormControl.ErrorMessage>
            {documentNumberInput.error}
          </FormControl.ErrorMessage>
        </FormControl>
        {showSubmitButton && <Button mt={4} onPress={handleSubmit}>Submit</Button>}
      </UBasicCard>
    );
  },
);

export default UNequiForm;
