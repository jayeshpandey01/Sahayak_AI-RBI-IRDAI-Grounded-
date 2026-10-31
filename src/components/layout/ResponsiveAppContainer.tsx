import React from 'react';
import {StyleSheet, View, useWindowDimensions, Platform} from 'react-native';

interface ResponsiveAppContainerProps {
  children: React.ReactNode;
}

const ResponsiveAppContainer: React.FC<ResponsiveAppContainerProps> = ({children}) => {
  const {width} = useWindowDimensions();
  const isDesktop = width >= 768;

  if (!isDesktop) {
    return <View style={styles.mobileContainer}>{children}</View>;
  }

  return (
    <View style={styles.desktopBackdrop}>
      <View style={styles.desktopCanvas}>
        {children}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  mobileContainer: {
    flex: 1,
    width: '100%',
    height: '100%',
    backgroundColor: '#FFFFFF',
  },
  desktopBackdrop: {
    flex: 1,
    width: '100%',
    height: '100%',
    backgroundColor: '#0C181B',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Platform.OS === 'web' ? 16 : 0,
    paddingHorizontal: Platform.OS === 'web' ? 16 : 0,
  },
  desktopCanvas: {
    width: '100%',
    maxWidth: 560,
    flex: 1,
    maxHeight: Platform.OS === 'web' ? ('calc(100vh - 32px)' as any) : '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: Platform.OS === 'web' ? 24 : 0,
    overflow: 'hidden',
    shadowColor: '#000000',
    shadowOffset: {width: 0, height: 16},
    shadowOpacity: 0.35,
    shadowRadius: 32,
    elevation: 12,
    borderWidth: Platform.OS === 'web' ? 1 : 0,
    borderColor: 'rgba(255, 255, 255, 0.12)',
  },
});

export default ResponsiveAppContainer;

