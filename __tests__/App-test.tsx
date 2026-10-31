/**
 * @format
 */

import 'react-native';
import React from 'react';
import {act} from 'react';
import App from '../App';

// Note: test renderer must be required after react-native.
import renderer from 'react-test-renderer';

it('renders the app and its home screen', async () => {
  jest.useFakeTimers();

  let app: renderer.ReactTestRenderer;
  await act(async () => {
    app = renderer.create(<App />);
  });

  expect(app!.toJSON()).not.toBeNull();

  await act(async () => {
    jest.advanceTimersByTime(333);
  });
  expect(app!.toJSON()).not.toBeNull();

  await act(async () => {
    app!.unmount();
  });
  jest.useRealTimers();
});
