/**
 * Sahayak AI — Multimodal Chat & Voice-to-Voice Client Utility
 * Handles audio recording transmission, text-to-speech playback, and RAG citations.
 */

export interface VoiceChatTimingBreakdown {
  stt_ms: number;
  rag_ms: number;
  llm_ms: number;
  tts_ms: number;
  total_ms: number;
}

export interface GroundedCitation {
  citation_id: string;
  document_name: string;
  version: string;
  clause: string;
  snippet: string;
  source_name?: string;
  source_url?: string;
  document_type?: string;
  effective_from?: string;
}

export interface GroundedRAGResponse {
  answer: string;
  citations: GroundedCitation[];
  source_documents: string[];
  confidence: number;
  disclaimer: string;
}

export interface VoiceChatResponse {
  transcript: string;
  reply_text: string;
  audio_base64?: string;
  content_type: string;
  language: string;
  rag_info?: GroundedRAGResponse;
  timings: VoiceChatTimingBreakdown;
  human_handoff?: any;
}

export interface ConversationTurn {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Send recorded audio to the unified E2E Voice-to-Voice endpoint.
 */
export async function sendVoiceChat(
  apiBaseUrl: string,
  audioBlob: Blob,
  language: 'en' | 'hi' | 'mr' | 'hinglish' = 'en',
  conversation: ConversationTurn[] = [],
  allowExternalProcessing: boolean = true,
  journeyId?: string,
  clientTranscript?: string
): Promise<VoiceChatResponse> {
  const formData = new FormData();
  let filename = 'recording.webm';
  if (audioBlob.type) {
    if (audioBlob.type.includes('mp4')) filename = 'recording.m4a';
    else if (audioBlob.type.includes('wav')) filename = 'recording.wav';
    else if (audioBlob.type.includes('ogg')) filename = 'recording.ogg';
    else if (audioBlob.type.includes('aac')) filename = 'recording.aac';
    else if (audioBlob.type.includes('mpeg') || audioBlob.type.includes('mp3')) filename = 'recording.mp3';
  }
  (formData as any).append('file', audioBlob, filename);
  formData.append('language', language);
  formData.append('allow_external_processing', String(allowExternalProcessing));
  if (journeyId) {
    formData.append('journey_id', journeyId);
  }
  if (clientTranscript && clientTranscript.trim()) {
    formData.append('client_transcript', clientTranscript.trim());
  }
  if (conversation.length > 0) {
    formData.append('conversation', JSON.stringify(conversation.slice(-8)));
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/chat/voice/e2e`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Voice chat error (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Send text message with optional audio response.
 */
export async function sendTextChat(
  apiBaseUrl: string,
  message: string,
  language: 'en' | 'hi' | 'mr' | 'hinglish' = 'en',
  conversation: ConversationTurn[] = [],
  includeAudio: boolean = true,
  allowExternalProcessing: boolean = true,
  journeyId?: string
): Promise<VoiceChatResponse> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      language,
      conversation: conversation.slice(-8),
      include_audio: includeAudio,
      allow_external_processing: allowExternalProcessing,
      journey_id: journeyId,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chat error (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return {
    transcript: message,
    reply_text: data.reply,
    audio_base64: data.audio_base64,
    content_type: 'audio/mpeg',
    language: data.language || language,
    rag_info: data.rag_info,
    timings: { stt_ms: 0, rag_ms: 0, llm_ms: 0, tts_ms: 0, total_ms: 0 },
    human_handoff: data.human_handoff,
  };
}

/**
 * Play base64 encoded audio string in browser or web environment.
 */
export function playBase64Audio(
  base64Audio: string,
  onEnd?: () => void,
  onError?: (err?: any) => void
): any {
  if (typeof window !== 'undefined' && (window as any).Audio) {
    try {
      const audio = new (window as any).Audio(`data:audio/mpeg;base64,${base64Audio}`);
      if (onEnd) {
        audio.onended = onEnd;
      }
      if (onError) {
        audio.onerror = onError;
      }
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err: any) => {
          console.warn('Audio playback was prevented by browser policy:', err);
          if (onError) onError(err);
        });
      }
      return audio;
    } catch (err) {
      console.warn('Audio construction failed:', err);
      if (onError) onError(err);
    }
  }
  return null;
}

export const playAudioBase64 = playBase64Audio;

/**
 * Browser Speech Synthesis fallback for web environments when server TTS audio is not returned.
 */
export function speakTextWithBrowser(
  text: string,
  language: 'en' | 'hi' | 'mr' | 'hinglish' = 'en',
  onEnd?: () => void,
  onError?: (err?: any) => void
): any {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
      // Remove regulatory citation brackets, URLs, and markdown before speaking
      const cleanText = text
        .replace(/\[\^?\d+\]/g, '')
        .replace(/https?:\/\/\S+/g, '')
        .replace(/[*_#`~]/g, '')
        .trim();

      if (!cleanText) {
        if (onEnd) onEnd();
        return null;
      }

      const utterance = new (window as any).SpeechSynthesisUtterance(cleanText);
      utterance.lang = language === 'mr' ? 'mr-IN' : (language === 'hi' || language === 'hinglish' ? 'hi-IN' : 'en-IN');
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        const languagePrefix = language === 'hinglish' ? 'hi' : language;
        const matchedVoice = voices.find(v => {
          const l = (v.lang || '').toLowerCase();
          return l.startsWith(languagePrefix);
        });
        if (matchedVoice) {
          utterance.voice = matchedVoice;
        }
      }

      if (onEnd) {
        utterance.onend = onEnd;
      }
      if (onError) {
        utterance.onerror = (e: any) => {
          console.warn('SpeechSynthesis error:', e);
          if (onError) onError(e);
        };
      }

      window.speechSynthesis.speak(utterance);
      return utterance;
    } catch (err) {
      console.warn('Browser SpeechSynthesis failed to initialize:', err);
      if (onError) onError(err);
    }
  }
  return null;
}

/**
 * Cancel and stop any ongoing speech synthesis or audio playback.
 */
export function stopAllSpeech(): void {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {}
  }
}

