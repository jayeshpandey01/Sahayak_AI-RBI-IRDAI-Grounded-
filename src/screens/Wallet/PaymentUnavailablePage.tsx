import React from 'react';
import {useNavigation} from '@react-navigation/native';
import {Alert, Box, HStack, Text} from 'native-base';
import UBubblePageNavigationAndOneButton from '../../components/molecules/UBubblePageNavigationAndOneButton';
import TitleAndSubtitle from '../../components/atoms/TitleAndSubtitle';

type Props = {title: string; message: string};

const PaymentUnavailablePage = ({title, message}: Props) => {
  const navigation = useNavigation<any>();
  return (
    <UBubblePageNavigationAndOneButton
      bubbleColor="tertiary.100"
      topComponent={
        <Box marginY={10}>
          <TitleAndSubtitle
            title={title}
            subtitle="This payment action is unavailable."
          />
        </Box>
      }
      downComponent={
        <Alert status="warning" borderRadius="lg">
          <HStack space={3} alignItems="flex-start">
            <Alert.Icon mt={1} />
            <Text flex={1} color="text.800">
              {message}
            </Text>
          </HStack>
        </Alert>
      }
      buttonTitle="Back to wallet"
      onPressBackButton={() => navigation.goBack()}
      onPressButton={() => navigation.goBack()}
    />
  );
};

export default PaymentUnavailablePage;
