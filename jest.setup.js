jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

jest.mock('react-native-safe-area-context', () => {
  const safeAreaMock = require('react-native-safe-area-context/jest/mock');
  return safeAreaMock.default ?? safeAreaMock;
});

jest.mock('@expo/vector-icons', () => {
  const React = require('react');
  const {Text} = require('react-native');
  const MockIcon = ({name}) => React.createElement(Text, null, name);

  return new Proxy(
    {},
    {
      get: (_target, iconPack) =>
        iconPack === '__esModule' ? false : MockIcon,
    },
  );
});
