import React from 'react';
import {
  Box,
  Button,
  Center,
  HStack,
  Icon,
  IconButton,
  Image,
  Progress,
  ScrollView,
  VStack,
} from 'native-base';
import {useAuth} from '../contexts/AuthContext';
import UBasicBubblePage from '../components/molecules/UBasicBubblePage';
import {
  MaterialCommunityIcons,
  Ionicons,
  Feather,
} from '@expo/vector-icons';
import {useNavigation} from '@react-navigation/native';
import UText from '../components/atoms/UText';
import UBackgroundCard from '../components/atoms/UBackgroundCard';
import {useLanguage} from '../contexts/LanguageContext';
import {formatRupees} from '../utils/currency';

const Home = () => {
  const {user, logout} = useAuth();
  const navigation = useNavigation();
  const {t, getGreeting} = useLanguage();

  const userDisplayName = user?.full_name ? user.full_name.trim().split(' ')[0] : undefined;

  return (
    <UBasicBubblePage
      smallBubble
      bubbleColor={'secondary.600'}
      topComponent={
        <Box mb={10}>
          <HStack justifyContent={'space-between'} mb={5}>
            <HStack alignItems={'center'} space={2}>
              <IconButton
                variant="ghost"
                rounded={100}
                size={15}
                icon={
                  <Image
                    alt="user default icon"
                    source={require('../assets/icons/userIcon.png')}
                  />
                }
                onPress={() => navigation.navigate('UserMenu' as never)}
              />
              <UText size={18} weight={400} color="text.50">
                {getGreeting(userDisplayName)}
              </UText>
            </HStack>
            <HStack>
              <IconButton
                variant="ghost"
                rounded="sm"
                icon={
                  <Icon
                    as={Ionicons}
                    name="earth-sharp"
                    color="text.50"
                    size={7}
                  />
                }
                onPress={() => navigation.navigate('Deposit' as never)}
              />
              <IconButton
                variant="ghost"
                rounded="sm"
                icon={
                  <Icon
                    as={Ionicons}
                    name="school-outline"
                    color="text.50"
                    size={7}
                  />
                }
                onPress={() => navigation.navigate('Deposit' as never)}
              />
            </HStack>
          </HStack>
          <VStack alignItems={'center'}>
            <UText color="text.50" size={16} weight={500}>
              {t('dreamTitle')}
            </UText>
            <HStack space={1} alignItems="flex-end">
              <UText weight={700} size={48} color="text.50">
                ₹ {formatRupees(150000)}
              </UText>
            </HStack>
            <UText color="text.50" size={11}>
              Savings goal target · demo only (not wallet balance)
            </UText>
            <Box w="90%" maxW="400">
              <Progress value={45} mx="4" />
            </Box>
          </VStack>
          <Center my={5}>
            <Button
              variant={'outline'}
              style={{
                borderColor: 'rgba(0, 238, 201, 0.55)',
                borderRadius: 100,
                borderWidth: 2,
              }}>
              <HStack alignItems={'center'} space={1}>
                <UText size={12} weight={500} color="text.50">
                  {t('dreamDetails')}
                </UText>
                <UText size={15} color="text.50">
                  👉
                </UText>
              </HStack>
            </Button>
          </Center>
          <HStack justifyContent="space-around" mt={6} mb={1} zIndex={2}>
            <VStack alignItems="center">
              <IconButton
                variant="ghost"
                rounded="full"
                size={14}
                bg="#335459"
                _web={{cursor: 'pointer'}}
                _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                _pressed={{transform: [{scale: 0.95}]}}
                icon={
                  <Icon
                    as={MaterialCommunityIcons}
                    name="download-outline"
                    color="text.50"
                    size={'lg'}
                  />
                }
                onPress={() => navigation.navigate('Deposit' as never)}
              />
              <UText text weight={400} size={12} color="text.50">
                {t('deposit')}
              </UText>
            </VStack>
            <VStack alignItems="center">
              <IconButton
                variant="ghost"
                rounded="full"
                size={14}
                bg="#335459"
                _web={{cursor: 'pointer'}}
                _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                _pressed={{transform: [{scale: 0.95}]}}
                icon={
                  <Icon
                    as={MaterialCommunityIcons}
                    name="upload-outline"
                    color="text.50"
                    size={'lg'}
                  />
                }
                onPress={() => navigation.navigate('Withdraw' as never)}
              />
              <UText text weight={400} size={12} color="text.50">
                {t('withdraw')}
              </UText>
            </VStack>
            <VStack alignItems="center">
              <IconButton
                variant="ghost"
                rounded="full"
                size={14}
                bg="#335459"
                _web={{cursor: 'pointer'}}
                _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                _pressed={{transform: [{scale: 0.95}]}}
                icon={<Icon as={Feather} name="send" color="text.50" size="md" />}
                onPress={() => navigation.navigate('Send' as never)}
              />
              <UText text weight={400} size={12} color="text.50">
                {t('send')}
              </UText>
            </VStack>
            <VStack alignItems="center">
              <IconButton
                variant="ghost"
                rounded="full"
                size={14}
                bg="#335459"
                _web={{cursor: 'pointer'}}
                _hover={{bg: '#254449', transform: [{scale: 1.08}]}}
                _pressed={{transform: [{scale: 0.95}]}}
                icon={
                  <Icon as={Feather} name="plus" color="text.50" size={'lg'} />
                }
                onPress={() => navigation.navigate('UserMenu' as never)}
              />
              <UText text weight={400} size={12} color="text.50">
                {t('more')}
              </UText>
            </VStack>
          </HStack>
          <Box
            position={'absolute'}
            left={0}
            bottom={0}
            mb={-1}
            zIndex={-1}
            opacity={0.85}>
            <Image
              source={require('../assets/icons/principalMenuIcon.png')}
              alt="dream maker icon"
            />
          </Box>
        </Box>
      }
      downComponent={
        <>
          <Box flex={1} my={5}>
            <UText size={16} weight={500} color="secondary.500">
              {t('ourServices')}
            </UText>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} flexGrow={1} my={2}>
              <HStack space={3} pb={2}>
                <UBackgroundCard
                  bgColor="empathy.300"
                  style={{width: 220, minWidth: 200}}>
                  <VStack zIndex={2}>
                    <UText weight={500} text color="text.900" size={18}>
                      {t('invest')}
                    </UText>
                    <UText
                      weight={400}
                      text
                      color="text.700"
                      size={10}
                      style={{width: '75%'}}>
                      {t('investSubtitle')}
                    </UText>
                    <Box mt={4}>
                      <UText weight={700} size={30} color="secondary.500">
                        15.3%
                      </UText>
                      <UText
                        weight={400}
                        size={10}
                        color="text.700"
                        style={{top: -7}}>
                        {t('annualInterest')}
                      </UText>
                    </Box>
                  </VStack>
                  <Box
                    position={'absolute'}
                    right={0}
                    bottom={0}
                    mb={-1}
                    zIndex={1}>
                    <Image
                      source={require('../assets/icons/ucoinIconMd.png')}
                      alt="ucoin icon"
                    />
                  </Box>
                </UBackgroundCard>
                <UBackgroundCard
                  bgColor="primary.600"
                  style={{width: 220, minWidth: 200}}>
                  <VStack zIndex={2}>
                    <UText weight={500} text color="text.900" size={18}>
                      {t('cashback')}
                    </UText>
                    <UText
                      weight={400}
                      text
                      color="text.700"
                      size={10}
                      style={{width: '75%'}}>
                      {t('cashbackSubtitle')}
                    </UText>
                    <Box mt={4}>
                      <UText weight={700} size={30} color="secondary.500">
                        20%
                      </UText>
                      <UText
                        weight={400}
                        size={10}
                        color="text.700"
                        style={{top: -7, position: 'absolute'}}>
                        {t('upTo')}
                      </UText>
                      <UText
                        weight={400}
                        size={10}
                        color="text.700"
                        style={{top: -7}}>
                        cashback
                      </UText>
                    </Box>
                  </VStack>
                  <Box position={'absolute'} right={0} bottom={0} mb={-1}>
                    <Image
                      source={require('../assets/icons/jetpackCashbackIconMd.png')}
                      alt="cashback icon"
                    />
                  </Box>
                </UBackgroundCard>
              </HStack>
            </ScrollView>
          </Box>
        </>
      }
    />
  );
};

export default Home;
