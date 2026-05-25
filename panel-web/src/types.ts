export type VoiceProcessEntry = {
  pid: string;
  name: string;
  cmd: string;
};

export type VoiceSnapshot = {
  generated_at: string;
  version?: string;
  badge: {
    state: 'running' | 'listening' | 'paused' | 'warn' | 'stopped' | 'unknown';
    label: string;
    hint: string;
    color: string;
  };
  badge_label?: string;
  summary: {
    tray_running: boolean;
    bridge_running: boolean;
    mode: string;
    health: string;
    paused: boolean;
    last_error: string;
    last_event: string;
  };
  control: {
    paused: boolean;
  };
  config: VoiceConfig;
  env?: VoiceConfig;
  processes: {
    tray: VoiceProcessEntry[];
    bridge: VoiceProcessEntry[];
  };
  logs: string[];
  status_lines: string[];
  log_state: {
    tray_state: string;
    bridge_state: string;
    mode: string;
    last_event: string;
    last_error: string;
    last_good: string;
  };
};

export type VoiceConfig = {
  mic_device: string;
  hotkey: string;
  feedback_mode: string;
  feedback_voice: string;
  wake_phrases: string;
  stt_language: string;
  stt_model: string;
  wake_energy: string;
  silence_rms: string;
  block_seconds: string;
  wake_window_seconds: string;
  silence_timeout_seconds: string;
  max_command_seconds: string;
  webhook_sync: string;
  webhook_timeout: string;
};

export type VoiceDevice = {
  index: number;
  name: string;
  max_input_channels: number;
  default_samplerate: number;
  hostapi?: number;
  selected: boolean;
};
