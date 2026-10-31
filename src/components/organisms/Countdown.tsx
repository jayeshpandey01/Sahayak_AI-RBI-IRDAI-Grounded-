import React, {useEffect, useState} from 'react';
import {Text, Button} from 'native-base';
import {useLanguage} from '../../contexts/LanguageContext';

interface CountdownProps {
  initialCount: number;
  onEndCount: () => void;
}

const Countdown: React.FC<CountdownProps> = ({initialCount, onEndCount}) => {
  const [counter, setCounter] = useState(initialCount);
  const [requestNewCode, setRequestNewCode] = useState(false);
  const {t} = useLanguage();

  useEffect(() => {
    if (counter > 0) {
      const timer = setTimeout(() => {
        setCounter(counter - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else {
      setRequestNewCode(true);
    }
  }, [counter]);

  const handleNewCodeRequest = () => {
    setCounter(initialCount);
    setRequestNewCode(false);
    onEndCount();
  };

  return counter > 0 ? (
    <Text
      textAlign={'center'}
      fontWeight={400}
      color={'neutral.500'}
      fontSize={14}>
      {t('newCodeIn')} {Math.floor(counter / 60)}:
      {('0' + (counter % 60)).slice(-2)}
    </Text>
  ) : (
    <Button
      variant="link"
      onPress={handleNewCodeRequest}
      fontWeight={400}
      textAlign={'center'}
      fontSize={14}>
      {t('requestNewCode')}
    </Button>
  );
};

export default Countdown;
