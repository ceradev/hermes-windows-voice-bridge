import type {
    CustomCommand as CustomCommandModel,
    RecentActivity,
    SessionRecord,
    ChatMessage,
    AudioDevice,
    SendMessageResponse,
    AddCustomCommandResponse,
} from '../types';

type ConfigUpdates = Record<string, unknown>;
type CustomCommandPayload = Omit<CustomCommandModel, 'id'>;

export type ShortcutsConfig = {
    hotkey: string;
    mute_hotkey: string;
    pause_hotkey: string;
};

export type OverlayMode = 'mini' | 'full' | string;
export type ListeningState = 'idle' | 'listening' | 'hidden' | string;

export type RuntimeState = {
    lifecycle?: string;
    overlay_state?: string;
    last_transcript?: string;
    last_response_preview?: string;
    last_error?: string;
    session?: Record<string, unknown>;
    shortcut?: Record<string, unknown>;
    services?: Record<string, unknown>;
    runtime?: {
        connection_status?: string;
        hotkey?: string;
        mic_device?: number | null;
        mic_device_name?: string;
        mic_device_hostapi?: number | null;
        overlay_enabled?: boolean;
        overlay_mode?: OverlayMode;
        overlay_x?: number | null;
        overlay_y?: number | null;
        overlay_visible?: boolean;
        listening_state?: ListeningState;
        overlay_detail?: string;
        overlay_request?: string;
        overlay_response?: string;
    };
};

type PywebviewApi = {
    get_config?: () => Promise<ConfigUpdates>;
    update_config?: (updates: ConfigUpdates) => Promise<boolean>;
    get_runtime_state?: () => Promise<RuntimeState>;
    get_sessions?: () => Promise<SessionRecord[]>;
    create_session?: (name: string) => Promise<string>;
    switch_session?: (id: string) => Promise<boolean>;
    delete_session?: (id: string) => Promise<void>;
    rename_session?: (id: string, name: string) => Promise<boolean>;
    get_messages?: (sessionId: string) => Promise<ChatMessage[]>;
    get_recent_activity?: () => Promise<RecentActivity[]>;
    send_message?: (text: string) => Promise<SendMessageResponse>;
    speak_text?: (text: string) => Promise<boolean>;
    get_audio_devices?: () => Promise<AudioDevice[]>;
    check_health?: () => Promise<boolean>;
    minimize_to_tray?: () => void;
    maximize_window?: () => void;
    close_app?: () => void;
    exit_app?: () => void;
    toggle_mini_mode?: (enable: boolean) => Promise<boolean>;
    pause_app?: (paused: boolean) => Promise<boolean>;
    restart_app?: () => Promise<boolean>;
    get_custom_commands?: () => Promise<CustomCommandModel[]>;
    add_custom_command?: (cmd: CustomCommandPayload) => Promise<AddCustomCommandResponse>;
    update_custom_command?: (id: string, cmd: CustomCommandPayload) => Promise<boolean>;
    delete_custom_command?: (id: string) => Promise<boolean>;
    test_custom_command?: (id: string) => Promise<boolean>;
};

declare global {
    interface Window {
        pywebview?: {
            api?: PywebviewApi;
        };
    }
}

export const api = {
    getConfig: async (): Promise<ConfigUpdates> => {
        if (window.pywebview?.api?.get_config) return await window.pywebview.api.get_config();
        return {};
    },

    updateConfig: async (updates: ConfigUpdates): Promise<boolean> => {
        if (window.pywebview?.api?.update_config) return await window.pywebview.api.update_config(updates);
        return false;
    },

    getSessions: async (): Promise<SessionRecord[]> => {
        if (window.pywebview?.api?.get_sessions) return await window.pywebview.api.get_sessions();
        return [];
    },

    createSession: async (name: string): Promise<string> => {
        if (window.pywebview?.api?.create_session) return await window.pywebview.api.create_session(name);
        return "";
    },

    switchSession: async (id: string): Promise<boolean> => {
        if (window.pywebview?.api?.switch_session) return await window.pywebview.api.switch_session(id);
        return false;
    },

    deleteSession: async (id: string): Promise<boolean> => {
        if (window.pywebview?.api?.delete_session) {
            await window.pywebview.api.delete_session(id);
            return true;
        }
        return false;
    },

    renameSession: async (id: string, name: string): Promise<boolean> => {
        if (window.pywebview?.api?.rename_session) return await window.pywebview.api.rename_session(id, name);
        return false;
    },

    getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
        if (window.pywebview?.api?.get_messages) return await window.pywebview.api.get_messages(sessionId);
        return [];
    },

    getRecentActivity: async (): Promise<RecentActivity[]> => {
        if (window.pywebview?.api?.get_recent_activity) return await window.pywebview.api.get_recent_activity();
        return [];
    },

    sendMessage: async (text: string): Promise<SendMessageResponse> => {
        if (window.pywebview?.api?.send_message) return await window.pywebview.api.send_message(text);
        return { success: false, response: "Mock mode: API not connected" };
    },

    speakText: async (text: string): Promise<boolean> => {
        if (window.pywebview?.api?.speak_text) return await window.pywebview.api.speak_text(text);
        return false;
    },

    getAudioDevices: async (): Promise<AudioDevice[]> => {
        if (window.pywebview?.api?.get_audio_devices) return await window.pywebview.api.get_audio_devices();
        return [];
    },

    checkHealth: async (): Promise<boolean> => {
        if (window.pywebview?.api?.check_health) return await window.pywebview.api.check_health();
        return false;
    },

    minimizeToTray: (): void => {
        if (window.pywebview?.api?.minimize_to_tray) window.pywebview.api.minimize_to_tray();
    },

    maximizeWindow: (): void => {
        if (window.pywebview?.api?.maximize_window) window.pywebview.api.maximize_window();
    },

    closeApp: (): void => {
        if (window.pywebview?.api?.close_app) window.pywebview.api.close_app();
    },

    exitApp: (): void => {
        if (window.pywebview?.api?.exit_app) window.pywebview.api.exit_app();
    },

    toggleMiniMode: async (enable: boolean): Promise<boolean> => {
        if (window.pywebview?.api?.toggle_mini_mode) return await window.pywebview.api.toggle_mini_mode(enable);
        return false;
    },

    pauseApp: async (paused: boolean): Promise<boolean> => {
        if (window.pywebview?.api?.pause_app) return await window.pywebview.api.pause_app(paused);
        return false;
    },

    restartApp: async (): Promise<boolean> => {
        if (window.pywebview?.api?.restart_app) return await window.pywebview.api.restart_app();
        return false;
    },

    getCustomCommands: async (): Promise<CustomCommandModel[]> => {
        if (window.pywebview?.api?.get_custom_commands) return await window.pywebview.api.get_custom_commands();
        return [];
    },

    addCustomCommand: async (cmd: CustomCommandPayload): Promise<AddCustomCommandResponse> => {
        if (window.pywebview?.api?.add_custom_command) return await window.pywebview.api.add_custom_command(cmd);
        return { ...cmd, id: "" };
    },

    updateCustomCommand: async (id: string, cmd: CustomCommandPayload): Promise<boolean> => {
        if (window.pywebview?.api?.update_custom_command) return await window.pywebview.api.update_custom_command(id, cmd);
        return false;
    },

    deleteCustomCommand: async (id: string): Promise<boolean> => {
        if (window.pywebview?.api?.delete_custom_command) return await window.pywebview.api.delete_custom_command(id);
        return false;
    },

    testCustomCommand: async (id: string): Promise<boolean> => {
        if (window.pywebview?.api?.test_custom_command) return await window.pywebview.api.test_custom_command(id);
        return false;
    },

    getShortcuts: async (): Promise<ShortcutsConfig> => {
        const cfg = await api.getConfig();
        return {
            hotkey: (cfg.hotkey as string) || "CTRL+SHIFT+H",
            mute_hotkey: (cfg.mute_hotkey as string) || "",
            pause_hotkey: (cfg.pause_hotkey as string) || "",
        };
    },

    updateShortcuts: async (shortcuts: ShortcutsConfig): Promise<boolean> => {
        return await api.updateConfig(shortcuts);
    },

    getRuntimeState: async (): Promise<RuntimeState | null> => {
        if (window.pywebview?.api?.get_runtime_state) return await window.pywebview.api.get_runtime_state();
        return null;
    },
};
