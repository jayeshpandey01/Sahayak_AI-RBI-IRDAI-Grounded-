import React from 'react';
import {Box, ScrollView} from 'native-base';
import {SafeAreaView} from 'react-native';

interface UBasicScrollableWrapperProps {
  children?: React.ReactNode;
  backgroundColor?: string;
}

const UBasicScrollableWrapper: React.FC<UBasicScrollableWrapperProps> = ({
  children,
  backgroundColor = 'white',
}) => {
  return (
    <Box flex={1} pt={5} bgColor={backgroundColor}>
      <SafeAreaView style={{flex: 1}}>
        <Box maxW={560} w="100%" alignSelf="center" flex={1}>
          <ScrollView px={5} showsVerticalScrollIndicator={false}>
            {children}
          </ScrollView>
        </Box>
      </SafeAreaView>
    </Box>
  );
};

export default UBasicScrollableWrapper;
