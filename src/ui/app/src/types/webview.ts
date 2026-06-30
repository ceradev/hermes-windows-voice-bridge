export type CustomCommandActionType =
  | 'open_app'
  | 'web_search'
  | 'system_volume'
  | 'tts_speak'
  | 'hotkey';

export type CustomCommandAction = {
  type: CustomCommandActionType | string;
  target: string;
};

export type CustomCommand = {
  id: string;
  name: string;
  trigger_phrases: string[];
  actions: CustomCommandAction[];
};

export type CustomCommandPayload = Omit<CustomCommand, 'id'>;

export type OverlayMode = 'mini' | 'full' | (string & {});

export type ListeningState =
  | 'idle'
  | 'listening'
  | 'hidden'
  | 'thinking'
  | 'processing'
  | 'speaking'
  | 'responding'
  | (string & {});

export type FeedbackMode = 'both' | 'voice' | 'beep' | 'off' | (string & {});

export type HermesConfigValue =
  | string
  | number
  | boolean
  | null
  | string[]
  | CustomCommand[];

export type HermesConfig = {
  webhook_url: string;
  webhook_secret: string;
  webhook_sync: boolean;
  webhook_timeout: number;
  webhook_user_id: string;
  api_base_url: string;
  api_token: string;
  app_language: string;
  app_platform: string;
  app_version: string;
  wake_phrases: string[] | string;
  hotkey: string;
  mute_hotkey?: string;
  pause_hotkey?: string;
  visual_hotkey?: string;
  mic_device: number | null;
  mic_device_name: string;
  mic_device_hostapi: number | null;
  tts_enabled: boolean;
  feedback_mode: FeedbackMode;
  feedback_voice: string;
  autostart: boolean;
  theme: string;
  minimize_to_tray: boolean;
  notifications: boolean;
  stt_language: string;
  stt_model: string;
  wake_energy: number;
  silence_rms: number;
  block_seconds: number;
  wake_window_seconds: number;
  initial_timeout_seconds: number;
  silence_timeout_seconds: number;
  max_command_seconds: number;
  custom_commands: CustomCommand[];
  overlay_enabled: boolean;
  overlay_mode: OverlayMode;
  overlay_x: number | null;
  overlay_y: number | null;
  notifications_enabled: boolean;
  [key: string]: HermesConfigValue | undefined;
};

export type HermesConfigUpdate = Partial<HermesConfig>;

export type ShortcutsConfig = {
  hotkey: string;
  mute_hotkey: string;
  pause_hotkey: string;
};

export type SessionRecord = {
  id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
  is_active?: boolean | 0 | 1;
  remote_session_id?: string | null;
  title_source?: 'system' | 'manual' | 'auto' | string;
};

export type ChatMessage = {
  id: string | number;
  session_id?: string;
  role: 'user' | 'hermes' | 'system' | string;
  content: string;
  source?: string | null;
  status?: string | null;
  latency_ms?: number | null;
  created_at?: string;
  timestamp?: string;
};

export type MessageStats = {
  today: number;
  week: number;
};

export type RecentActivity = {
  timestamp: string;
  type: 'voice' | 'command' | string;
  text: string;
  status: 'success' | 'error' | string;
};

export type AudioDevice = {
  index: number;
  name: string;
  max_input_channels: number;
  default_samplerate: number;
  hostapi?: number;
  selected?: boolean;
};

export type SendMessageResponse =
  | {
      success: true;
      response: string;
      message_id: string | number;
      latencyMs: number;
      remoteSessionId?: string;
    }
  | {
      success: false;
      error?: string;
      response?: string;
      message_id?: string | number;
    };

export type ServiceStatus = {
  state: string;
  detail: string;
  pid: number | null;
  latency_ms: number | null;
  last_updated_at: string;
};

export type RuntimeState = {
  lifecycle: string;
  overlay_state: string;
  last_transcript: string;
  last_response_preview: string;
  last_error: string;
  session: {
    authenticated: boolean;
    user_id: string;
    display_name: string;
    token_expires_at: string;
    remember_me: boolean;
    restoration_source: string;
    last_error: string;
  };
  shortcut: {
    accelerator: string;
    is_listening: boolean;
    has_conflict: boolean;
    conflict_with: string;
    last_pressed: string[];
    preview_keys: Array<{ key: string; pressed: boolean }>;
  };
  services: {
    tray: ServiceStatus;
    bridge: ServiceStatus;
    api: ServiceStatus;
    hermes: ServiceStatus;
    tts: ServiceStatus;
  };
  runtime: RuntimeStatus;
};

export type RuntimeStatus = {
  connection_status: string;
  hotkey: string;
  mic_device: number | null;
  mic_device_name: string;
  mic_device_hostapi: number | null;
  overlay_enabled: boolean;
  overlay_mode: OverlayMode;
  overlay_x: number | null;
  overlay_y: number | null;
  overlay_visible: boolean;
  listening_state: ListeningState;
  overlay_detail: string;
  overlay_request: string;
  overlay_response: string;
};

export type QuickCommand = {
  id: string;
  label: string;
};
