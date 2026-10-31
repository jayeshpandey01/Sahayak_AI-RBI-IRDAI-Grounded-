import React from 'react';
import {View} from 'react-native';
import {InputTemplateUbanku} from './InputTemplateUbanku';

interface PhoneLoginFormProps {
  phone: string;
  onChangePhone: (text: string) => void;
  password: string;
  onChangePassword: (text: string) => void;
}

const PhoneLoginForm = ({
  phone,
  onChangePhone,
  password,
  onChangePassword,
}: PhoneLoginFormProps) => {
  return (
    <View>
      <InputTemplateUbanku
        type="number-pad"
        value={phone}
        onChangeText={onChangePhone}
        placeholder={'Mobile Number'}
        imageSource={require('../../assets/icons/phoneIcon.png')}
      />
      <InputTemplateUbanku
        value={password}
        onChangeText={onChangePassword}
        placeholder={'Password'}
        imageSource={require('../../assets/icons/lockIcon.png')}
      />
    </View>
  );
};
export default PhoneLoginForm;
