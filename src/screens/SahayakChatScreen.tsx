import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  Divider,
  HStack,
  Icon,
  IconButton,
  Input,
  Pressable,
  ScrollView,
  Spinner,
  Text,
  VStack,
} from 'native-base';
import {
  Animated,
  Dimensions,
  Easing,
  Modal,
  Platform,
  StyleSheet,
  View,
} from 'react-native';
import {MaterialCommunityIcons, Feather, Ionicons} from '@expo/vector-icons';
import {useFocusEffect, useNavigation, useRoute} from '@react-navigation/native';
import {useAuth} from '../contexts/AuthContext';
import {useLanguage} from '../contexts/LanguageContext';
import {sendChatMessage} from '../services/sahayakApi';
import {apiErrorMessage, API_BASE_URL} from '../services/apiClient';
import {
  playBase64Audio,
  sendVoiceChat,
  speakTextWithBrowser,
  stopAllSpeech,
} from '../utils/voiceClient';

const ink = '#17343A';
const muted = '#61777B';
const teal = '#087F78';
const lightTeal = '#E6F4F1';
const cardBg = '#FFFFFF';
const surfaceBg = '#F5F8F7';

interface CitationItem {
  citation_id: string;
  document_name: string;
  clause: string;
  version: string;
  source_name?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[];
  audioBase64?: string;
  timestamp: string;
  disclaimer?: string;
}

const PRESET_QUERIES = [
  'What are RBI rules regarding Key Fact Statement (KFS)?',
  'Can loan recovery agents call me at midnight?',
  'Are foreclosure charges allowed on floating-rate loans?',
  'What is the UPI dispute resolution timeline under NPCI?',
  'What is the IRDAI free-look period for life insurance?',
  'How do I file a complaint with the RBI Integrated Ombudsman?',
];

const SahayakChatScreen = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const {authToken, user} = useAuth();
  const {t, chatLanguage, setChatLanguage} = useLanguage();

  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [includeAudio, setIncludeAudio] = useState(false);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [allowExternal, setAllowExternal] = useState(true);

  // Voice Demo Popup Modal State
  const [voiceModalVisible, setVoiceModalVisible] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'listening' | 'processing' | 'speaking'>('idle');
  const [voiceStatusText, setVoiceStatusText] = useState('Start speaking');
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [voiceResponseText, setVoiceResponseText] = useState('');
  const [isPaused, setIsPaused] = useState(false);

  // Animation values for Voice Modal (matches screenshot)
  const orbScaleAnim = useRef(new Animated.Value(1)).current;
  const orbGlowAnim = useRef(new Animated.Value(0.6)).current;
  const modalScaleAnim = useRef(new Animated.Value(0.92)).current;
  const modalOpacityAnim = useRef(new Animated.Value(0)).current;

  // 4 animated waveform dots
  const dot1Anim = useRef(new Animated.Value(0.3)).current;
  const dot2Anim = useRef(new Animated.Value(0.3)).current;
  const dot3Anim = useRef(new Animated.Value(0.3)).current;
  const dot4Anim = useRef(new Animated.Value(0.3)).current;

  // MediaRecorder refs for browser audio recording
  const mediaRecorderRef = useRef<any>(null);
  const mediaStreamRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const currentAudioElementRef = useRef<any>(null);
  const speechRecognitionRef = useRef<any>(null);
  const liveTranscriptRef = useRef<string>('');
  const silenceTimerRef = useRef<any>(null);
  const [isMicMuted, setIsMicMuted] = useState(false);

  const scrollViewRef = useRef<any>(null);

  const initialGreeting = useMemo<ChatMessage>(() => ({
    id: 'welcome_1',
    role: 'assistant',
    content:
      chatLanguage === 'hi'
        ? 'नमस्ते! मैं सहायक AI हूँ — आपका वित्तीय एवं ऋण परामर्श सह-पायलट। आप मुझसे RBI डिजिटल लेंडिंग नियमों, KFS (Key Fact Statement), रिकवरी एजेंट कॉलिंग समय, फ्लोटिंग लोन प्रीपेमेंट, या बीमा नियमों के बारे में पूछ सकते हैं।'
        : chatLanguage === 'mr'
          ? 'नमस्कार! मी सहाय्यक AI आहे — तुमचा आर्थिक माहिती आणि कर्ज तयारीसाठीचा सहकारी. RBI डिजिटल कर्ज नियम, KFS, वसुली एजंट, कर्जाचे हप्ते किंवा पेमेंटबद्दल विचारा.'
          : 'Hello! I am Sahayak AI — your grounded financial information and loan readiness copilot. Ask me about RBI digital lending norms, Key Fact Statements (KFS), recovery agent calling hours, floating-rate loan foreclosure bans, insurance free-look rules, or payments.',
    timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
  }), [chatLanguage]);

  const [messages, setMessages] = useState<ChatMessage[]>([initialGreeting]);

  useEffect(() => {
    setMessages(previous => previous.length === 1 && previous[0].id === 'welcome_1' ? [initialGreeting] : previous);
  }, [initialGreeting]);

  // Handle incoming params like paymentOrderId or initial query
  useEffect(() => {
    if (route.params?.paymentOrderId) {
      const q = `Can you explain the status of payment order ${route.params.paymentOrderId}?`;
      sendMessage(q, route.params.paymentOrderId);
    } else if (route.params?.initialQuery) {
      sendMessage(route.params.initialQuery);
    }
  }, [route.params]);

  // Orb breathing pulse animation
  useEffect(() => {
    let animLoop: Animated.CompositeAnimation;
    if (voiceModalVisible) {
      // Smooth breathing loop
      animLoop = Animated.loop(
        Animated.sequence([
          Animated.parallel([
            Animated.timing(orbScaleAnim, {
              toValue: voiceStatus === 'listening' ? 1.14 : voiceStatus === 'speaking' ? 1.1 : 1.05,
              duration: voiceStatus === 'listening' ? 1000 : 1400,
              easing: Easing.inOut(Easing.ease),
              useNativeDriver: true,
            }),
            Animated.timing(orbGlowAnim, {
              toValue: 1.0,
              duration: voiceStatus === 'listening' ? 1000 : 1400,
              useNativeDriver: true,
            }),
          ]),
          Animated.parallel([
            Animated.timing(orbScaleAnim, {
              toValue: 1.0,
              duration: voiceStatus === 'listening' ? 1000 : 1400,
              easing: Easing.inOut(Easing.ease),
              useNativeDriver: true,
            }),
            Animated.timing(orbGlowAnim, {
              toValue: 0.5,
              duration: voiceStatus === 'listening' ? 1000 : 1400,
              useNativeDriver: true,
            }),
          ]),
        ]),
      );
      animLoop.start();
    }
    return () => {
      animLoop?.stop();
    };
  }, [voiceModalVisible, voiceStatus]);

  // Staggered animated wave dots
  useEffect(() => {
    let dotLoop: Animated.CompositeAnimation;
    if (voiceModalVisible) {
      const createDotAnim = (anim: Animated.Value, delay: number) =>
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(anim, {
            toValue: 1.0,
            duration: 350,
            useNativeDriver: true,
          }),
          Animated.timing(anim, {
            toValue: 0.3,
            duration: 350,
            useNativeDriver: true,
          }),
        ]);

      dotLoop = Animated.loop(
        Animated.parallel([
          createDotAnim(dot1Anim, 0),
          createDotAnim(dot2Anim, 150),
          createDotAnim(dot3Anim, 300),
          createDotAnim(dot4Anim, 450),
        ]),
      );
      dotLoop.start();
    }
    return () => {
      dotLoop?.stop();
    };
  }, [voiceModalVisible]);

  // Open Voice Modal with smooth entrance animation
  const openVoiceModal = () => {
    setVoiceModalVisible(true);
    setVoiceStatus('idle');
    setVoiceStatusText('Start speaking');
    setVoiceTranscript('');
    setVoiceResponseText('');
    setIsPaused(false);

    modalScaleAnim.setValue(0.9);
    modalOpacityAnim.setValue(0);
    Animated.parallel([
      Animated.spring(modalScaleAnim, {
        toValue: 1,
        tension: 65,
        friction: 8,
        useNativeDriver: true,
      }),
      Animated.timing(modalOpacityAnim, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start();

    // Auto-prompt microphone on browser
    setTimeout(() => {
      handleToggleRecording();
    }, 400);
  };

  // SpeechRecognition helpers for real-time live voice recognition
  const startSpeechRecognition = () => {
    if (typeof window !== 'undefined') {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SR) {
        try {
          if (speechRecognitionRef.current) {
            try { speechRecognitionRef.current.abort(); } catch (e) {}
          }
          const recognition = new SR();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = chatLanguage === 'hi' ? 'hi-IN' : chatLanguage === 'mr' ? 'mr-IN' : 'en-IN';

          recognition.onresult = (event: any) => {
            let fullText = '';
            for (let i = 0; i < event.results.length; ++i) {
              fullText += event.results[i][0].transcript;
            }
            const clean = fullText.trim();
            if (clean) {
              liveTranscriptRef.current = clean;
              setVoiceTranscript(clean);
              setVoiceStatusText(`Listening: "${clean.length > 28 ? clean.slice(-28) + '...' : clean}"`);

              // Silence auto-detection: auto-send after 2.2s of silence following speech
              if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
              }
              silenceTimerRef.current = setTimeout(() => {
                if (voiceStatus === 'listening' && (liveTranscriptRef.current || voiceTranscript).trim()) {
                  finishRecordingAndSend();
                }
              }, 2200);
            }
          };

          recognition.onerror = (e: any) => {
            console.warn('SpeechRecognition error:', e?.error);
            // If microphone turned off or permission revoked, exit listening mode
            if (e?.error === 'audio-capture' || e?.error === 'not-allowed') {
              handleMicrophoneOff();
            }
          };

          recognition.onspeechend = () => {
            if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = setTimeout(() => {
              if (voiceStatus === 'listening' && (liveTranscriptRef.current || voiceTranscript).trim()) {
                finishRecordingAndSend();
              }
            }, 1800);
          };

          recognition.onend = () => {
            // Check if mic tracks are muted or ended
            if (mediaStreamRef.current) {
              const tracks = mediaStreamRef.current.getAudioTracks();
              const allInactive = tracks.every((t: any) => t.muted || t.readyState === 'ended');
              if (allInactive) {
                handleMicrophoneOff();
              }
            }
          };

          recognition.start();
          speechRecognitionRef.current = recognition;
        } catch (err) {
          console.warn('SpeechRecognition failed to start:', err);
        }
      }
    }
  };

  const stopSpeechRecognition = () => {
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) {}
      speechRecognitionRef.current = null;
    }
  };

  // Called whenever microphone is turned off, muted, or disconnected
  const handleMicrophoneOff = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    stopSpeechRecognition();

    const recognizedText = (liveTranscriptRef.current || voiceTranscript).trim();

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }

    if (mediaStreamRef.current) {
      try {
        mediaStreamRef.current.getTracks().forEach((t: any) => t.stop());
      } catch (e) {}
      mediaStreamRef.current = null;
    }

    setIsMicMuted(true);

    // If user spoke words before turning off mic, send to AI!
    if (recognizedText) {
      setVoiceStatus('processing');
      setVoiceStatusText('Microphone off — Processing with RBI RAG...');
      processVoiceTextInput(recognizedText);
    } else {
      // Cleanly exit listening mode to idle so it never gets stuck
      setVoiceStatus('idle');
      setVoiceStatusText('Microphone off. Tap circle to speak');
    }
  };

  // Close Voice Modal with smooth exit
  const closeVoiceModal = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    stopSpeechRecognition();
    // Stop recording if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }
    if (mediaStreamRef.current) {
      try {
        mediaStreamRef.current.getTracks().forEach((t: any) => t.stop());
      } catch (e) {}
      mediaStreamRef.current = null;
    }
    // Stop any playing audio or speech synthesis
    stopAllSpeech();
    if (currentAudioElementRef.current && typeof currentAudioElementRef.current.pause === 'function') {
      try {
        currentAudioElementRef.current.pause();
      } catch (e) {}
    }
    currentAudioElementRef.current = null;
    setIsMicMuted(false);

    Animated.parallel([
      Animated.timing(modalScaleAnim, {
        toValue: 0.9,
        duration: 180,
        useNativeDriver: true,
      }),
      Animated.timing(modalOpacityAnim, {
        toValue: 0,
        duration: 180,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setVoiceModalVisible(false);
      setVoiceStatus('idle');
    });
  };

  // User finished speaking (via Pause button or circle tap): stop recording and send to AI!
  const finishRecordingAndSend = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    stopSpeechRecognition();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    } else {
      const spokenText = (liveTranscriptRef.current || voiceTranscript).trim();
      if (spokenText) {
        processVoiceTextInput(spokenText);
      } else {
        setVoiceStatus('idle');
        setVoiceStatusText('Start speaking');
      }
    }
  };

  // Toggle microphone on/off explicitly
  const handleToggleMic = () => {
    if (voiceStatus === 'listening') {
      handleMicrophoneOff();
    } else {
      setIsMicMuted(false);
      handleToggleRecording();
    }
  };

  // Start or Stop recording in the voice modal
  const handleToggleRecording = async () => {
    if (voiceStatus === 'listening') {
      // User tapped sphere while listening -> finish speaking and send to AI!
      finishRecordingAndSend();
      return;
    }

    if (voiceStatus === 'speaking' || voiceStatus === 'processing') {
      return;
    }

    liveTranscriptRef.current = '';
    setVoiceTranscript('');
    setIsMicMuted(false);

    // Check if in Web browser with MediaDevices
    if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});
        mediaStreamRef.current = stream;
        audioChunksRef.current = [];

        // Attach listener for hardware/system mic mute or disconnect
        stream.getAudioTracks().forEach((track: any) => {
          track.onended = () => {
            handleMicrophoneOff();
          };
          track.onmute = () => {
            handleMicrophoneOff();
          };
        });

        // Detect supported MIME type on the client
        let options: any = {};
        if (typeof MediaRecorder !== 'undefined' && (MediaRecorder as any).isTypeSupported) {
          const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/ogg;codecs=opus',
            'audio/wav',
          ];
          for (const t of types) {
            if ((MediaRecorder as any).isTypeSupported(t)) {
              options.mimeType = t;
              break;
            }
          }
        }

        const recorder = new (window as any).MediaRecorder(stream, options);
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (e: any) => {
          if (e.data && e.data.size > 0) {
            audioChunksRef.current.push(e.data);
          }
        };

        recorder.onstop = async () => {
          if (mediaStreamRef.current) {
            try {
              mediaStreamRef.current.getTracks().forEach((t: any) => t.stop());
            } catch (e) {}
            mediaStreamRef.current = null;
          }
          stopSpeechRecognition();
          const cleanMime = (options.mimeType || 'audio/webm').split(';')[0];
          const audioBlob = new Blob(audioChunksRef.current, {type: cleanMime});
          if (audioBlob.size < 400 && !liveTranscriptRef.current) {
            setVoiceStatus('idle');
            setVoiceStatusText('Start speaking');
            return;
          }
          await processVoiceInput(audioBlob);
        };

        recorder.start();
        setVoiceStatus('listening');
        setVoiceStatusText('Listening... Speak now');
        startSpeechRecognition();
      } catch (err: any) {
        console.warn('Microphone access denied or unavailable:', err);
        setVoiceStatus('idle');
        setVoiceStatusText('Tap circle or presets to ask');
      }
    } else {
      // Native environment without Web mediaDevices
      startSpeechRecognition();
      setVoiceStatus('listening');
      setVoiceStatusText('Listening... Speak now');
    }
  };

  // Fallback text processing when audio is not available but speech was recognized
  const processVoiceTextInput = async (spokenText: string) => {
    setVoiceStatus('processing');
    setVoiceStatusText('Processing & Grounding...');

    try {
      const convPayload = messages
        .filter(m => m.id !== 'welcome_1')
        .slice(-6)
        .map(m => ({role: m.role, content: m.content}));

      const res = await sendChatMessage(authToken, {
        message: spokenText,
        language: chatLanguage,
        allow_external_processing: allowExternal,
        include_audio: true,
        conversation: convPayload,
      });

      setVoiceTranscript(spokenText);
      setVoiceResponseText(res.reply || '');

      const userTurn: ChatMessage = {
        id: `usr_voice_${Date.now()}`,
        role: 'user',
        content: spokenText,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
      };

      const citations: CitationItem[] = (res.rag_info?.citations || []).map((c: any) => ({
        citation_id: c.citation_id,
        document_name: c.document_name,
        clause: c.clause,
        version: c.version,
        source_name: c.source_name || c.document_name,
      }));

      const assistantTurn: ChatMessage = {
        id: `asst_voice_${Date.now()}`,
        role: 'assistant',
        content: res.reply || 'No response received.',
        citations,
        audioBase64: res.audio_base64 || undefined,
        disclaimer: res.rag_info?.disclaimer,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
      };

      setMessages(prev => [...prev, userTurn, assistantTurn]);
      scrollToBottom();

      const finishSpeaking = () => {
        setVoiceStatus('idle');
        setVoiceStatusText('Start speaking');
        currentAudioElementRef.current = null;
      };

      const speakWithClientFallback = () => {
        if (res.reply) {
          setVoiceStatus('speaking');
          setVoiceStatusText('Sahayak is speaking...');
          const utterance = speakTextWithBrowser(
            res.reply,
            chatLanguage,
            finishSpeaking,
            finishSpeaking
          );
          currentAudioElementRef.current = utterance;
          if (!utterance) finishSpeaking();
        } else {
          finishSpeaking();
        }
      };

      if (res.audio_base64) {
        setVoiceStatus('speaking');
        setVoiceStatusText('Sahayak is speaking...');
        const audio = playBase64Audio(res.audio_base64, finishSpeaking, speakWithClientFallback);
        currentAudioElementRef.current = audio;
        if (!audio) speakWithClientFallback();
      } else {
        speakWithClientFallback();
      }
    } catch (err: any) {
      setVoiceStatus('idle');
      setVoiceStatusText('Tap circle or pause to try again');
      setError(apiErrorMessage(err));
    }
  };

  // Process recorded audio through unified E2E voice endpoint
  const processVoiceInput = async (audioBlob: Blob) => {
    setVoiceStatus('processing');
    setVoiceStatusText('Processing & Grounding...');

    try {
      const convPayload = messages
        .filter(m => m.id !== 'welcome_1')
        .slice(-6)
        .map(m => ({role: m.role, content: m.content}));

      const recognizedText = (liveTranscriptRef.current || voiceTranscript).trim();

      const res = await sendVoiceChat(
        API_BASE_URL,
        audioBlob,
        chatLanguage,
        convPayload,
        allowExternal,
        undefined,
        recognizedText
      );

      const finalTranscript = res.transcript || recognizedText || 'Spoken query';
      setVoiceTranscript(finalTranscript);
      setVoiceResponseText(res.reply_text || '');

      // Add user recognized speech turn to chat history
      const userTurn: ChatMessage = {
        id: `usr_voice_${Date.now()}`,
        role: 'user',
        content: finalTranscript,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
      };

      const citations: CitationItem[] = (res.rag_info?.citations || []).map((c: any) => ({
        citation_id: c.citation_id,
        document_name: c.document_name,
        clause: c.clause,
        version: c.version,
        source_name: c.source_name || c.document_name,
      }));

      const assistantTurn: ChatMessage = {
        id: `asst_voice_${Date.now()}`,
        role: 'assistant',
        content: res.reply_text,
        citations,
        audioBase64: res.audio_base64 || undefined,
        disclaimer: res.rag_info?.disclaimer,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
      };

      setMessages(prev => [...prev, userTurn, assistantTurn]);
      scrollToBottom();

      // Seamless Voice Playback:
      // 1. Play server-synthesized audio if present
      // 2. If server audio is missing or browser restricts autoplay, fallback to Web Speech API
      const finishSpeaking = () => {
        setVoiceStatus('idle');
        setVoiceStatusText('Start speaking');
        currentAudioElementRef.current = null;
      };

      const speakWithClientFallback = () => {
        if (res.reply_text) {
          setVoiceStatus('speaking');
          setVoiceStatusText('Sahayak is speaking...');
          const utterance = speakTextWithBrowser(
            res.reply_text,
            chatLanguage,
            finishSpeaking,
            finishSpeaking
          );
          currentAudioElementRef.current = utterance;
          if (!utterance) {
            finishSpeaking();
          }
        } else {
          finishSpeaking();
        }
      };

      if (res.audio_base64) {
        setVoiceStatus('speaking');
        setVoiceStatusText('Sahayak is speaking...');
        const audio = playBase64Audio(
          res.audio_base64,
          finishSpeaking,
          () => {
            // Audio playback error or autoplay block - fallback to speech synthesis
            speakWithClientFallback();
          }
        );
        currentAudioElementRef.current = audio;
        if (!audio) {
          speakWithClientFallback();
        }
      } else {
        speakWithClientFallback();
      }
    } catch (err: any) {
      setVoiceStatus('idle');
      setVoiceStatusText('Tap circle or pause to try again');
      setError(apiErrorMessage(err));
    }
  };

  // Toggle pause/resume or send in Voice Modal
  const handleTogglePause = () => {
    // When listening, clicking Pause sends the recorded audio and transcript to AI!
    if (voiceStatus === 'listening') {
      finishRecordingAndSend();
      return;
    }

    setIsPaused(prev => !prev);
    if (voiceStatus === 'speaking') {
      if (isPaused) {
        if (currentAudioElementRef.current && typeof currentAudioElementRef.current.play === 'function') {
          currentAudioElementRef.current.play();
        } else if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.resume();
        }
        setVoiceStatusText('Sahayak is speaking...');
      } else {
        if (currentAudioElementRef.current && typeof currentAudioElementRef.current.pause === 'function') {
          currentAudioElementRef.current.pause();
        } else if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.pause();
        }
        setVoiceStatusText('Paused');
      }
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({animated: true});
    }, 150);
  };

  const sendMessage = async (textToSend?: string, paymentOrderId?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
    };

    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInputMessage('');
    setError('');
    setLoading(true);
    scrollToBottom();

    try {
      const convPayload = nextMessages
        .filter(m => m.id !== 'welcome_1')
        .slice(-6)
        .map(m => ({role: m.role, content: m.content}));

      const res = await sendChatMessage(authToken, {
        message: text,
        language: chatLanguage,
        allow_external_processing: allowExternal,
        include_audio: includeAudio,
        conversation: convPayload,
        ...(paymentOrderId ? {payment_order_id: paymentOrderId, include_payment_context: true} : {}),
      });

      const citations: CitationItem[] = (res.rag_info?.citations || []).map((c: any) => ({
        citation_id: c.citation_id,
        document_name: c.document_name,
        clause: c.clause,
        version: c.version,
        source_name: c.source_name || c.document_name,
      }));

      const assistantMsg: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: res.reply || 'No response received.',
        citations,
        audioBase64: res.audio_base64 || undefined,
        disclaimer: res.rag_info?.disclaimer,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
      };

      setMessages(prev => [...prev, assistantMsg]);
      scrollToBottom();

      if (includeAudio) {
        handlePlayAudio(assistantMsg.id, res.audio_base64, assistantMsg.content);
      }
    } catch (err: any) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  };

  const handlePlayAudio = (msgId: string, base64Audio?: string, messageText?: string) => {
    if (!base64Audio && !messageText) return;
    setPlayingAudioId(msgId);
    if (base64Audio) {
      playBase64Audio(
        base64Audio,
        () => setPlayingAudioId(null),
        () => {
          if (messageText) {
            speakTextWithBrowser(
              messageText,
              chatLanguage,
              () => setPlayingAudioId(null),
              () => setPlayingAudioId(null)
            );
          } else {
            setPlayingAudioId(null);
          }
        }
      );
    } else if (messageText) {
      speakTextWithBrowser(
        messageText,
        chatLanguage,
        () => setPlayingAudioId(null),
        () => setPlayingAudioId(null)
      );
    }
  };

  const handleClearChat = () => {
    setMessages([initialGreeting]);
    setError('');
  };

  return (
    <Box flex={1} bg={surfaceBg} safeArea>
      {/* Header */}
      <HStack
        px={4}
        py={3}
        bg="white"
        alignItems="center"
        justifyContent="space-between"
        borderBottomWidth={1}
        borderBottomColor="#E2EBE9">
        <HStack space={3} alignItems="center">
          <Box bg={lightTeal} p={2} rounded="full">
            <Icon as={MaterialCommunityIcons} name="robot-outline" size={6} color={teal} />
          </Box>
          <VStack>
            <HStack space={2} alignItems="center">
              <Text bold fontSize="md" color={ink}>
                {t('sahayakAi') || 'Sahayak AI Copilot'}
              </Text>
              <Badge colorScheme="emerald" rounded="md" variant="subtle" _text={{fontSize: '2xs'}}>
                RBI / IRDAI Grounded
              </Badge>
            </HStack>
            <Text fontSize="xs" color={muted}>
              Multimodal Text & Voice Assistant
            </Text>
          </VStack>
        </HStack>
        <HStack space={1} alignItems="center">
          <IconButton
            icon={<Icon as={MaterialCommunityIcons} name="refresh" size={5} color={muted} />}
            onPress={handleClearChat}
            variant="ghost"
            rounded="full"
          />
        </HStack>
      </HStack>

      {/* Language Selection Bar in Clean Segmented Format */}
      <HStack
        bg="white"
        px={4}
        py={2}
        alignItems="center"
        justifyContent="space-between"
        borderBottomWidth={1}
        borderBottomColor="#E2EBE9">
        <HStack space={1.5} alignItems="center">
          <Icon as={MaterialCommunityIcons} name="translate" size={4} color={teal} />
          <Text fontSize="xs" fontWeight="600" color={ink}>
            {t('language') || 'Language'}
          </Text>
        </HStack>

        <HStack
          bg="#EEF5F3"
          p={1}
          rounded="full"
          borderWidth={1}
          borderColor="#D9E6E3"
          alignItems="center">
          {[
            {code: 'en', label: 'English'},
            {code: 'hi', label: 'हिन्दी'},
            {code: 'mr', label: 'मराठी'},
          ].map(item => {
            const isSelected = chatLanguage === item.code;
            return (
              <Pressable
                key={item.code}
                onPress={() => setChatLanguage(item.code as 'en' | 'hi' | 'mr')}
                px={3}
                py={1}
                rounded="full"
                bg={isSelected ? teal : 'transparent'}
                shadow={isSelected ? 1 : 0}>
                <Text
                  fontSize="xs"
                  fontWeight={isSelected ? '700' : '500'}
                  color={isSelected ? '#FFFFFF' : muted}>
                  {item.label}
                </Text>
              </Pressable>
            );
          })}
        </HStack>
      </HStack>

      {/* Suggested Quick Question Chips */}
      <Box py={2} px={3} bg="white" borderBottomWidth={1} borderBottomColor="#E2EBE9">
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <HStack space={2} py={1}>
            {PRESET_QUERIES.map((query, idx) => (
              <Pressable
                key={idx}
                onPress={() => sendMessage(query)}
                bg={surfaceBg}
                borderWidth={1}
                borderColor="#C9D8D5"
                px={3}
                py={1.5}
                rounded="full">
                <Text fontSize="2xs" color={ink} numberOfLines={1}>
                  {query}
                </Text>
              </Pressable>
            ))}
          </HStack>
        </ScrollView>
      </Box>

      {/* Chat Messages Stream */}
      <ScrollView
        ref={scrollViewRef}
        flex={1}
        px={4}
        py={3}
        contentContainerStyle={{paddingBottom: 24}}>
        <VStack space={4}>
          {messages.map(item => {
            const isUser = item.role === 'user';
            return (
              <Box
                key={item.id}
                alignSelf={isUser ? 'flex-end' : 'flex-start'}
                maxW="88%">
                <HStack space={2} alignItems="flex-start" flexDirection={isUser ? 'row-reverse' : 'row'}>
                  {!isUser && (
                    <Box bg={lightTeal} p={1.5} rounded="full" mt={1}>
                      <Icon as={MaterialCommunityIcons} name="shield-check-outline" size={4} color={teal} />
                    </Box>
                  )}
                  <VStack space={1} maxW="90%">
                    <Box
                      bg={isUser ? teal : cardBg}
                      p={3.5}
                      rounded="2xl"
                      shadow={isUser ? 0 : 1}
                      borderWidth={isUser ? 0 : 1}
                      borderColor="#E2EBE9">
                      <Text
                        color={isUser ? 'white' : ink}
                        fontSize="sm"
                        lineHeight="sm">
                        {item.content}
                      </Text>

                      {/* Verified Citations List */}
                      {item.citations && item.citations.length > 0 && (
                        <VStack mt={3} pt={2} borderTopWidth={1} borderTopColor="#EDF3F1" space={1.5}>
                          <HStack space={1} alignItems="center">
                            <Icon as={Feather} name="book-open" size={3} color={teal} />
                            <Text fontSize="2xs" bold color={teal}>
                              VERIFIED REGULATORY SOURCES:
                            </Text>
                          </HStack>
                          {item.citations.map((c, i) => (
                            <HStack
                              key={i}
                              bg="#F0F7F5"
                              p={1.5}
                              rounded="md"
                              alignItems="center"
                              justifyContent="space-between">
                              <VStack flex={1}>
                                <Text fontSize="2xs" bold color={ink}>
                                  {c.document_name}
                                </Text>
                                <Text fontSize="3xs" color={muted}>
                                  {c.clause} ({c.version})
                                </Text>
                              </VStack>
                              <Badge colorScheme="teal" variant="outline" rounded="sm" _text={{fontSize: '3xs'}}>
                                Grounded
                              </Badge>
                            </HStack>
                          ))}
                        </VStack>
                      )}

                      {/* Audio playback button for assistant responses */}
                      {!isUser && (
                        <Button
                          mt={2}
                          size="xs"
                          variant="outline"
                          borderColor={teal}
                          isLoading={playingAudioId === item.id}
                          leftIcon={
                            <Icon
                              as={MaterialCommunityIcons}
                              name={playingAudioId === item.id ? 'volume-high' : 'volume-medium'}
                              size={4}
                              color={teal}
                            />
                          }
                          onPress={() => handlePlayAudio(item.id, item.audioBase64, item.content)}
                          _text={{color: teal, fontSize: '2xs'}}>
                          Listen to audio
                        </Button>
                      )}
                    </Box>
                    <Text
                      fontSize="3xs"
                      color={muted}
                      alignSelf={isUser ? 'flex-end' : 'flex-start'}
                      px={1}>
                      {item.timestamp}
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            );
          })}

          {loading && (
            <HStack space={2} alignItems="center" bg="white" p={3} rounded="xl" alignSelf="flex-start" borderWidth={1} borderColor="#E2EBE9">
              <Spinner size="sm" color={teal} />
              <Text fontSize="xs" color={muted}>
                Sahayak AI is verifying regulatory sources...
              </Text>
            </HStack>
          )}

          {error ? (
            <Alert status="error" rounded="xl" mb={2}>
              <HStack space={2} alignItems="center">
                <Alert.Icon />
                <Text fontSize="xs" color="red.800" flex={1}>
                  {error}
                </Text>
              </HStack>
            </Alert>
          ) : null}
        </VStack>
      </ScrollView>

      {/* Input Toolbar */}
      <Box bg="white" px={3} py={2} borderTopWidth={1} borderTopColor="#E2EBE9">
        <HStack space={2} alignItems="center">
          <Input
            flex={1}
            value={inputMessage}
            onChangeText={setInputMessage}
            placeholder={
              chatLanguage === 'hi'
                ? 'ऋण, KFS, या RBI नियमों के बारे में पूछें...'
                : chatLanguage === 'mr'
                  ? 'कर्ज, KFS किंवा RBI नियमांबद्दल विचारा...'
                  : 'Ask about loans, KFS, or RBI rules...'
            }
            bg={surfaceBg}
            borderColor="#C9D8D5"
            rounded="xl"
            fontSize="sm"
            py={2.5}
            px={3}
            returnKeyType="send"
            onSubmitEditing={() => sendMessage()}
            InputRightElement={
              inputMessage.trim() ? (
                <IconButton
                  icon={<Icon as={MaterialCommunityIcons} name="close-circle" size={4} color={muted} />}
                  onPress={() => setInputMessage('')}
                  variant="ghost"
                  rounded="full"
                />
              ) : undefined
            }
          />
          <IconButton
            bg="#0F2D33"
            _pressed={{bg: '#173D44'}}
            rounded="xl"
            p={2.5}
            icon={<Icon as={MaterialCommunityIcons} name="microphone" size={5} color="#65D6BB" />}
            onPress={openVoiceModal}
          />
          <IconButton
            bg={teal}
            _pressed={{bg: '#066B65'}}
            rounded="xl"
            p={2.5}
            isLoading={loading}
            icon={<Icon as={Ionicons} name="send" size={4} color="white" />}
            onPress={() => sendMessage()}
          />
        </HStack>
      </Box>

      {/* ========================================================================= */}
      {/* ANIMATED VOICE-TO-VOICE POPUP MODAL (MATCHES USER SCREENSHOT EXACTLY)    */}
      {/* ========================================================================= */}
      <Modal
        visible={voiceModalVisible}
        transparent={true}
        animationType="none"
        onRequestClose={closeVoiceModal}>
        <View style={styles.modalBackdrop}>
          <Animated.View
            style={[
              styles.darkCardContainer,
              {
                opacity: modalOpacityAnim,
                transform: [{scale: modalScaleAnim}],
              },
            ]}>
            {/* Top Bar / Status badge inside card */}
            <View style={styles.topInfoBar}>
              <View style={styles.complianceBadge}>
                <Text style={styles.complianceText}>RBI KFS & CONDUCT VERIFIED</Text>
              </View>
            </View>

            {/* Central Animated Glowing White Sphere */}
            <Pressable onPress={handleToggleRecording} style={styles.sphereContainer}>
              <Animated.View
                style={[
                  styles.whiteOrb,
                  {
                    transform: [{scale: orbScaleAnim}],
                    shadowOpacity: orbGlowAnim,
                  },
                ]}
              />
            </Pressable>

            {/* Middle Section: Mic Icon + 4 Animated Waveform Dots + Status */}
            <View style={styles.statusSection}>
              <View style={styles.waveDotRow}>
                <Icon
                  as={MaterialCommunityIcons}
                  name="microphone"
                  size={4}
                  color="#FFFFFF"
                  style={{marginRight: 6}}
                />
                <Animated.View style={[styles.waveDot, {opacity: dot1Anim}]} />
                <Animated.View style={[styles.waveDot, {opacity: dot2Anim}]} />
                <Animated.View style={[styles.waveDot, {opacity: dot3Anim}]} />
                <Animated.View style={[styles.waveDot, {opacity: dot4Anim}]} />
              </View>

              <Text style={styles.statusLabelText}>{voiceStatusText}</Text>

              {voiceTranscript ? (
                <Text style={styles.transcriptPreviewText} numberOfLines={2}>
                  "{voiceTranscript}"
                </Text>
              ) : (
                <Text style={styles.hintSubtext}>Tap circle or pause when done speaking</Text>
              )}
            </View>

            {/* Bottom Controls: Pause Button (left) & Red Close "X" Button (center) */}
            <View style={styles.bottomControlsRow}>
              {/* Left: Pause Button */}
              <Pressable
                onPress={handleTogglePause}
                style={[
                  styles.pauseButton,
                  isPaused && {borderColor: '#65D6BB', backgroundColor: 'rgba(101, 214, 187, 0.2)'},
                ]}>
                <Icon
                  as={MaterialCommunityIcons}
                  name={isPaused ? 'play' : 'pause'}
                  size={5}
                  color={isPaused ? '#65D6BB' : '#FFFFFF'}
                />
              </Pressable>

              {/* Center: Red Circular "X" Close Button */}
              <Pressable onPress={closeVoiceModal} style={styles.closeRedButton}>
                <Icon as={MaterialCommunityIcons} name="close" size={6} color="#FFFFFF" />
              </Pressable>

              {/* Right: Microphone Turn Off / Mute Toggle Button */}
              <Pressable
                onPress={handleToggleMic}
                style={[
                  styles.pauseButton,
                  (isMicMuted || voiceStatus === 'idle') && {
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  },
                ]}>
                <Icon
                  as={MaterialCommunityIcons}
                  name={isMicMuted || voiceStatus === 'idle' ? 'microphone-off' : 'microphone'}
                  size={5}
                  color={isMicMuted || voiceStatus === 'idle' ? '#EF4444' : '#65D6BB'}
                />
              </Pressable>
            </View>

            {/* Home Indicator Bar */}
            <View style={styles.homeIndicatorBar} />
          </Animated.View>
        </View>
      </Modal>
    </Box>
  );
};

const {width: SCREEN_WIDTH} = Dimensions.get('window');

const styles = StyleSheet.create({
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(230, 245, 230, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 16,
    ...Platform.select({
      web: {
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
      } as any,
    }),
  },
  darkCardContainer: {
    width: '94%',
    maxWidth: 680,
    height: 440,
    backgroundColor: '#0A0A0C', // Deep black matching screenshot
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 24,
    paddingHorizontal: 20,
    shadowColor: '#000000',
    shadowOffset: {width: 0, height: 25},
    shadowOpacity: 0.55,
    shadowRadius: 40,
    elevation: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  topInfoBar: {
    width: '100%',
    alignItems: 'center',
    paddingTop: 4,
  },
  complianceBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  complianceText: {
    color: '#94A3B8',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1.2,
  },
  sphereContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 12,
  },
  whiteOrb: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: '#FFFFFF',
    shadowColor: '#FFFFFF',
    shadowOffset: {width: 0, height: 0},
    shadowRadius: 35,
    elevation: 20,
  },
  statusSection: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 4,
  },
  waveDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  waveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#FFFFFF',
    marginHorizontal: 3,
  },
  statusLabelText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  transcriptPreviewText: {
    color: '#A1A1AA',
    fontSize: 12,
    fontStyle: 'italic',
    textAlign: 'center',
    maxWidth: 320,
    marginTop: 4,
  },
  hintSubtext: {
    color: '#71717A',
    fontSize: 11,
    marginTop: 2,
  },
  bottomControlsRow: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    marginTop: 8,
  },
  pauseButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
  },
  pauseButtonSpacer: {
    width: 38,
    height: 38,
  },
  closeRedButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FF5A5F', // Coral red matching screenshot
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#FF5A5F',
    shadowOffset: {width: 0, height: 6},
    shadowOpacity: 0.45,
    shadowRadius: 16,
    elevation: 8,
  },
  homeIndicatorBar: {
    width: 120,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.85)',
    marginTop: 12,
  },
});

export default SahayakChatScreen;
