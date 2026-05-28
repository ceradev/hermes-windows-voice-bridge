import type { CustomCommand as CustomCommandModel, RecentActivity } from '../types';

type ConfigUpdates = Record<string, unknown>;
type CustomCommandPayload = Omit<CustomCommandModel, 'id'>;
type SessionRecord = { id: string; is_active?: boolean; [key: string]: unknown };

export type ShortcutsConfig = {
  hotkey: string;
  mute_hotkey: string;
  pause_hotkey: string;
};

type PywebviewApi = {
    get_config?: () => Promise<ConfigUpdates>;
    update_config?: (updates: ConfigUpdates) => Promise<boolean>;
    get_sessions?: () => Promise<SessionRecord[]>;
    create_session?: (name: string) => Promise<string>;
    switch_session?: (id: string) => Promise<boolean>;
    delete_session?: (id: string) => Promise<void>;
    get_messages?: (sessionId: string) => Promise<any[]>;
    get_recent_activity?: () => Promise<RecentActivity[]>;
    send_message?: (text: string) => Promise<{ success: boolean; response?: string }>;
    speak_text?: (text: string) => Promise<boolean>;
    get_audio_devices?: () => Promise<any[]>;
    check_health?: () => Promise<boolean>;
    minimize_to_tray?: () => void;
    maximize_window?: () => void;
    close_app?: () => void;
    exit_app?: () => void;
    toggle_mini_mode?: (enable: boolean) => Promise<boolean>;
    pause_app?: (paused: boolean) => Promise<boolean>;
    restart_app?: () => Promise<boolean>;
    get_custom_commands?: () => Promise<CustomCommandModel[]>;
    add_custom_command?: (cmd: CustomCommandPayload) => Promise<boolean>;
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
    getConfig: async () => {
        if (window.pywebview?.api?.get_config) return await window.pywebview.api.get_config();
        return {};
    },
    updateConfig: async (updates: ConfigUpdates) => {
        if (window.pywebview?.api?.update_config) return await window.pywebview.api.update_config(updates);
        return false;
    },
    getSessions: async () => {
        if (window.pywebview?.api?.get_sessions) return await window.pywebview.api.get_sessions();
        return [];
    },
    createSession: async (name: string) => {
        if (window.pywebview?.api?.create_session) return await window.pywebview.api.create_session(name);
        return "";
    },
    switchSession: async (id: string) => {
        if (window.pywebview?.api?.switch_session) return await window.pywebview.api.switch_session(id);
        return false;
    },
    deleteSession: async (id: string) => {
        if (window.pywebview?.api?.delete_session) return await window.pywebview.api.delete_session(id);
        return false;
    },
    getMessages: async (sessionId: string) => {
        if (window.pywebview?.api?.get_messages) return await window.pywebview.api.get_messages(sessionId);
        return [];
    },
    getRecentActivity: async () => {
        if (window.pywebview?.api?.get_recent_activity) return await window.pywebview.api.get_recent_activity();
        return [];
    },
    sendMessage: async (text: string) => {
        if (window.pywebview?.api?.send_message) return await window.pywebview.api.send_message(text);
        return { success: false, response: "Mock mode: API not connected" };
    },
    speakText: async (text: string) => {
        if (window.pywebview?.api?.speak_text) return await window.pywebview.api.speak_text(text);
        return false;
    },
    getAudioDevices: async () => {
        if (window.pywebview?.api?.get_audio_devices) return await window.pywebview.api.get_audio_devices();
        return [];
    },
    checkHealth: async () => {
        if (window.pywebview?.api?.check_health) return await window.pywebview.api.check_health();
        return false;
    },
    minimizeToTray: () => {
        if (window.pywebview?.api?.minimize_to_tray) window.pywebview.api.minimize_to_tray();
    },
    maximizeWindow: () => {
        if (window.pywebview?.api?.maximize_window) window.pywebview.api.maximize_window();
    },
    closeApp: () => {
        if (window.pywebview?.api?.close_app) window.pywebview.api.close_app();
    },
    exitApp: () => {
        if (window.pywebview?.api?.exit_app) window.pywebview.api.exit_app();
    },
    toggleMiniMode: async (enable: boolean) => {
        if (window.pywebview?.api?.toggle_mini_mode) return await window.pywebview.api.toggle_mini_mode(enable);
        return false;
    },
    pauseApp: async (paused: boolean) => {
        if (window.pywebview?.api?.pause_app) return await window.pywebview.api.pause_app(paused);
        return false;
    },
    restartApp: async () => {
        if (window.pywebview?.api?.restart_app) return await window.pywebview.api.restart_app();
        return false;
    },
    getCustomCommands: async () => {
        if (window.pywebview?.api?.get_custom_commands) return await window.pywebview.api.get_custom_commands();
        return [];
    },
    addCustomCommand: async (cmd: CustomCommandPayload) => {
        if (window.pywebview?.api?.add_custom_command) return await window.pywebview.api.add_custom_command(cmd);
        return false;
    },
    updateCustomCommand: async (id: string, cmd: CustomCommandPayload) => {
        if (window.pywebview?.api?.update_custom_command) return await window.pywebview.api.update_custom_command(id, cmd);
        return false;
    },
    deleteCustomCommand: async (id: string) => {
        if (window.pywebview?.api?.delete_custom_command) return await window.pywebview.api.delete_custom_command(id);
        return false;
    },
    testCustomCommand: async (id: string) => {
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
    updateShortcuts: async (shortcuts: ShortcutsConfig) => {
        return await api.updateConfig(shortcuts);
    },
};
