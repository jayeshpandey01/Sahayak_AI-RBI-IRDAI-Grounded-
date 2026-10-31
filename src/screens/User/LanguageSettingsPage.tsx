import React from 'react';
import {Box, Radio, VStack, HStack, Text, Icon} from 'native-base';
import {useNavigation} from '@react-navigation/native';
import {Feather} from '@expo/vector-icons';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UBasicCard from '../../components/atoms/UBasicCard';
import UText from '../../components/atoms/UText';
import ULine from '../../components/atoms/ULine';
import {useLanguage, LanguageCode} from '../../contexts/LanguageContext';

const LanguageSettingsPage: React.FC = () => {
  const navigation = useNavigation();
  const {currentLanguage, setLanguage, chatLanguage, setChatLanguage, languages, t} = useLanguage();

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleSelectLanguage = (value: string) => {
    setLanguage(value as LanguageCode);
  };

  const handleSelectChatLanguage = (value: string) => {
    setChatLanguage(value as LanguageCode);
  };

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={handleBackPress}>
      <VStack space={4} my={3}>
        <HStack alignItems="center" space={2}>
          <Icon as={Feather} name="globe" size={6} color="primary.600" />
          <UText title size={20} weight={700}>
            {t('languageSettings')}
          </UText>
        </HStack>

        <UText size={14} color="text.600" weight={400}>
          {t('selectLanguage')}
        </UText>

        <UBasicCard>
          <Radio.Group
            name="languageSelection"
            value={currentLanguage}
            onChange={handleSelectLanguage}
            space={4}>
            {languages.map((lang, index) => (
              <React.Fragment key={lang.code}>
                <Radio value={lang.code} my={1}>
                  <Box ml={2}>
                    <Text fontWeight={currentLanguage === lang.code ? 700 : 500} fontSize="md" color="text.900">
                      {lang.nativeLabel}
                    </Text>
                    <Text fontSize="xs" color="text.500">
                      {lang.label}
                    </Text>
                  </Box>
                </Radio>
                {index < languages.length - 1 && <ULine />}
              </React.Fragment>
            ))}
          </Radio.Group>
        </UBasicCard>

        <Box p={3} rounded="md" bg="primary.50">
          <Text fontSize="xs" color="primary.800">
            ✓ {t('languageUpdated')}
          </Text>
        </Box>

        <VStack space={3} pt={3}>
          <UText title size={18} weight={700}>{t('aiChatLanguage')}</UText>
          <Text fontSize="sm" color="text.600">
            {t('aiChatLanguageHint')}
          </Text>
          <UBasicCard>
            <Radio.Group
              name="aiChatLanguageSelection"
              value={chatLanguage}
              onChange={handleSelectChatLanguage}
              space={4}>
              {languages.map((lang, index) => (
                <React.Fragment key={lang.code}>
                  <Radio value={lang.code} my={1}>
                    <Box ml={2}>
                      <Text fontWeight={chatLanguage === lang.code ? 700 : 500} fontSize="md" color="text.900">
                        {lang.nativeLabel}
                      </Text>
                      <Text fontSize="xs" color="text.500">{lang.label}</Text>
                    </Box>
                  </Radio>
                  {index < languages.length - 1 && <ULine />}
                </React.Fragment>
              ))}
            </Radio.Group>
          </UBasicCard>
        </VStack>
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default LanguageSettingsPage;

