import React from 'react';
import {Pressable, HStack, Icon} from 'native-base';
import {Feather} from '@expo/vector-icons';
import {GestureResponderEvent} from 'react-native';
import UText from '../../atoms/UText';

interface Props {
  icon: string;
  text: string;
  onPress: (event: GestureResponderEvent) => void;
}

const UuserMenuPressable: React.FC<Props> = ({icon, text, onPress}) => {
  return (
    <Pressable
      onPress={onPress}
      _web={{cursor: 'pointer'}}
      _hover={{bg: 'gray.100'}}
      rounded="lg"
      px={2}
      py={2}
      mx={-2}>
      {({isPressed}) => (
        <HStack
          alignItems="center"
          justifyContent="space-between"
          style={{
            transform: [{scale: isPressed ? 0.98 : 1}],
          }}>
          <HStack space={3} alignItems="center">
            <Icon as={Feather} name={icon} color="text.700" size={5} />
            <UText weight={400} size={14} color="text.700">
              {text}
            </UText>
          </HStack>

          <Icon as={Feather} name="chevron-right" color="text.500" size={5} />
        </HStack>
      )}
    </Pressable>
  );
};

export default UuserMenuPressable;
