import React, {useState, useEffect} from 'react';
import {
  Box,
  Button,
  FormControl,
  HStack,
  Icon,
  Input,
  Text,
  VStack,
  WarningOutlineIcon,
} from 'native-base';
import {useNavigation} from '@react-navigation/native';
import {Feather} from '@expo/vector-icons';
import UBasicScrollableNavigationWrapper from '../../components/molecules/UBasicScrollableNavigationWrapper';
import UBasicCard from '../../components/atoms/UBasicCard';
import UText from '../../components/atoms/UText';
import ULine from '../../components/atoms/ULine';
import {useAuth} from '../../contexts/AuthContext';
import {useLanguage} from '../../contexts/LanguageContext';

const ProfileDetailsPage: React.FC = () => {
  const navigation = useNavigation();
  const {user, updateProfile} = useAuth();
  const {t} = useLanguage();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (user?.full_name) {
      setFullName(user.full_name);
    }
  }, [user?.full_name]);

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleSaveName = async () => {
    const trimmed = fullName.trim();
    if (!trimmed) {
      setErrorMessage(t('nameRequired'));
      return;
    }
    setErrorMessage('');
    setIsSaving(true);
    try {
      await updateProfile({full_name: trimmed});
      setSuccessMessage(t('profileUpdated'));
      setIsEditing(false);
      setTimeout(() => {
        setSuccessMessage('');
      }, 3500);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <UBasicScrollableNavigationWrapper onPressBackButton={handleBackPress}>
      <VStack space={4} my={3}>
        <HStack alignItems="center" space={2}>
          <Icon as={Feather} name="user" size={6} color="primary.600" />
          <UText title size={20} weight={700}>
            {t('profileDetails')}
          </UText>
        </HStack>

        {successMessage ? (
          <Box p={3} rounded="md" bg="primary.50">
            <Text fontSize="xs" color="primary.800">
              ✓ {successMessage}
            </Text>
          </Box>
        ) : null}

        <UBasicCard>
          <VStack space={4}>
            <HStack justifyContent="space-between" alignItems="center">
              <UText weight={600} size={16} color="text.800">
                {t('accountDetails')}
              </UText>
              {!isEditing && (
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="secondary"
                  leftIcon={<Icon as={Feather} name="edit-2" size={4} />}
                  onPress={() => setIsEditing(true)}>
                  {t('editProfile')}
                </Button>
              )}
            </HStack>

            <ULine />

            {isEditing ? (
              <VStack space={3}>
                <FormControl isInvalid={!!errorMessage}>
                  <FormControl.Label>
                    <Text fontSize="xs" fontWeight={500} color="text.500">
                      {t('fullName')}
                    </Text>
                  </FormControl.Label>
                  <Input
                    value={fullName}
                    onChangeText={text => {
                      setFullName(text);
                      if (errorMessage) setErrorMessage('');
                    }}
                    placeholder={t('fullName')}
                    autoFocus
                    size="md"
                    borderRadius="md"
                  />
                  {errorMessage ? (
                    <FormControl.ErrorMessage leftIcon={<WarningOutlineIcon size="xs" />}>
                      {errorMessage}
                    </FormControl.ErrorMessage>
                  ) : null}
                </FormControl>

                <HStack space={2} justifyContent="flex-end" mt={2}>
                  <Button
                    size="sm"
                    variant="ghost"
                    onPress={() => {
                      setFullName(user?.full_name || '');
                      setIsEditing(false);
                      setErrorMessage('');
                    }}>
                    {t('cancel')}
                  </Button>
                  <Button
                    size="sm"
                    bg="primary.600"
                    _pressed={{bg: 'primary.700'}}
                    isLoading={isSaving}
                    onPress={handleSaveName}>
                    {t('saveChanges')}
                  </Button>
                </HStack>
              </VStack>
            ) : (
              <Box>
                <Text fontSize="xs" color="text.500" fontWeight={500}>
                  {t('fullName')}
                </Text>
                <Text fontSize="md" color="text.900" fontWeight={600} mt={1}>
                  {user?.full_name || '—'}
                </Text>
              </Box>
            )}

            <ULine />

            <Box>
              <Text fontSize="xs" color="text.500" fontWeight={500}>
                {t('email')}
              </Text>
              <Text fontSize="md" color="text.900" fontWeight={500} mt={1}>
                {user?.email || '—'}
              </Text>
            </Box>

            <ULine />

            <Box>
              <Text fontSize="xs" color="text.500" fontWeight={500}>
                {t('role')}
              </Text>
              <Text fontSize="md" color="text.900" fontWeight={500} mt={1} textTransform="capitalize">
                {user?.role || 'Customer'}
              </Text>
            </Box>

            <ULine />

            <Box>
              <Text fontSize="xs" color="text.500" fontWeight={500}>
                {t('userId')}
              </Text>
              <Text fontSize="xs" color="text.700" fontWeight={400} mt={1}>
                {user?.id ? String(user.id) : '—'}
              </Text>
            </Box>

            {user?.created_at && (
              <>
                <ULine />
                <Box>
                  <Text fontSize="xs" color="text.500" fontWeight={500}>
                    {t('registeredOn')}
                  </Text>
                  <Text fontSize="xs" color="text.700" fontWeight={400} mt={1}>
                    {new Date(user.created_at).toLocaleDateString()}
                  </Text>
                </Box>
              </>
            )}
          </VStack>
        </UBasicCard>
      </VStack>
    </UBasicScrollableNavigationWrapper>
  );
};

export default ProfileDetailsPage;

