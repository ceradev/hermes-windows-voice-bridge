import type {
    AudioDevice,
    ChatMessage,
    CustomCommand,
    CustomCommandPayload,
    HermesConfig,
    HermesConfigUpdate,
    QuickCommand,
    RecentActivity,
    RuntimeStatus,
    RuntimeState,
    SendMessageResponse,
    SessionRecord,
    ShortcutsConfig,
} from '../types/webview';

export type {
    AudioDevice,
    ChatMessage,
    CustomCommand,
    CustomCommandPayload,
    HermesConfig,
    HermesConfigUpdate,
    QuickCommand,
    RecentActivity,
    RuntimeStatus,
    RuntimeState,
    SendMessageResponse,
    SessionRecord,
    ShortcutsConfig,
} from '../types/webview';

type PywebviewApi = {
    show_error?: (title: string, message?: string) => Promise<boolean>;
    get_runtime_state?: () => Promise<RuntimeState>;
    navigate_to?: (path: string) => Promise<void>;
    get_config?: () => Promise<HermesConfig>;
    update_config?: (updates: HermesConfigUpdate) => Promise<boolean>;
    get_sessions?: () => Promise<SessionRecord[]>;
    create_session?: (name: string) => Promise<string>;
    switch_session?: (sessionId: string) => Promise<boolean>;
    delete_session?: (sessionId: string) => Promise<void>;
    rename_session?: (sessionId: string, newName: string) => Promise<boolean>;
    get_messages?: (sessionId: string) => Promise<ChatMessage[]>;
    get_recent_activity?: () => Promise<RecentActivity[]>;
    save_vps_token?: (token: string) => Promise<boolean>;
    get_vps_token?: () => Promise<string>;
    get_custom_commands?: () => Promise<CustomCommand[]>;
    add_custom_command?: (command: CustomCommandPayload) => Promise<CustomCommand>;
    update_custom_command?: (id: string, command: CustomCommandPayload) => Promise<boolean>;
    delete_custom_command?: (id: string) => Promise<boolean>;
    test_custom_command?: (id: string) => Promise<boolean>;
    get_audio_devices?: () => Promise<AudioDevice[]>;
    check_health?: () => Promise<boolean>;
    send_message?: (text: string, imageBase64?: string | null, source?: string) => Promise<SendMessageResponse>;
    speak_text?: (text: string) => Promise<boolean>;
    capture_hotkey?: (timeout?: number) => Promise<string>;
    check_hotkey_conflict?: (hotkey: string) => Promise<boolean>;
    get_quick_commands?: () => Promise<QuickCommand[]>;
    run_quick_command?: (commandId: string) => Promise<boolean>;
    notify_tray?: (title: string, message: string) => Promise<boolean>;
    log_local_action?: (requestText: string, responseText: string) => Promise<boolean>;
    toggle_mini_mode?: (enable: boolean) => Promise<boolean>;
    minimize_to_tray?: () => Promise<void>;
    maximize_window?: () => Promise<void>;
    close_app?: () => Promise<void>;
    exit_app?: () => Promise<void>;
    pause_app?: (paused: boolean) => Promise<boolean>;
    restart_app?: () => Promise<boolean>;
};

declare global {
    interface Window {
        pywebview?: {
            api?: PywebviewApi;
        };
    }
}

const getPywebviewApi = (): PywebviewApi | undefined => window.pywebview?.api;

export const api = {
    showError: async (title: string, message = ''): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.show_error) return bridge.show_error(title, message);
        return false;
    },

    getConfig: async (): Promise<HermesConfigUpdate> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_config) return bridge.get_config();
        return {};
    },

    updateConfig: async (updates: HermesConfigUpdate): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.update_config) return bridge.update_config(updates);
        return false;
    },

    getSessions: async (): Promise<SessionRecord[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_sessions) return bridge.get_sessions();
        return [];
    },

    createSession: async (name: string): Promise<string> => {
        const bridge = getPywebviewApi();
        if (bridge?.create_session) return bridge.create_session(name);
        return '';
    },

    switchSession: async (id: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.switch_session) return bridge.switch_session(id);
        return false;
    },

    deleteSession: async (id: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (!bridge?.delete_session) return false;
        await bridge.delete_session(id);
        return true;
    },

    renameSession: async (id: string, name: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.rename_session) return bridge.rename_session(id, name);
        return false;
    },

    getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_messages) return bridge.get_messages(sessionId);
        return [];
    },

    getRecentActivity: async (): Promise<RecentActivity[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_recent_activity) return bridge.get_recent_activity();
        return [];
    },

    saveVpsToken: async (token: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.save_vps_token) return bridge.save_vps_token(token);
        return false;
    },

    getVpsToken: async (): Promise<string> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_vps_token) return bridge.get_vps_token();
        return '';
    },

    getCustomCommands: async (): Promise<CustomCommand[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_custom_commands) return bridge.get_custom_commands();
        return [];
    },

    addCustomCommand: async (command: CustomCommandPayload): Promise<CustomCommand> => {
        const bridge = getPywebviewApi();
        if (bridge?.add_custom_command) return bridge.add_custom_command(command);
        return { ...command, id: '' };
    },

    updateCustomCommand: async (id: string, command: CustomCommandPayload): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.update_custom_command) return bridge.update_custom_command(id, command);
        return false;
    },

    deleteCustomCommand: async (id: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.delete_custom_command) return bridge.delete_custom_command(id);
        return false;
    },

    testCustomCommand: async (id: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.test_custom_command) return bridge.test_custom_command(id);
        return false;
    },

    getAudioDevices: async (): Promise<AudioDevice[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_audio_devices) return bridge.get_audio_devices();
        return [];
    },

    checkHealth: async (): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.check_health) return bridge.check_health();
        return false;
    },

    sendMessage: async (text: string, imageBase64: string | null = null, source = 'voice'): Promise<SendMessageResponse> => {
        const bridge = getPywebviewApi();
        if (bridge?.send_message) return bridge.send_message(text, imageBase64, source);
        return { success: false, response: 'Mock mode: API not connected' };
    },

    speakText: async (text: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.speak_text) return bridge.speak_text(text);
        return false;
    },

    captureHotkey: async (timeout?: number): Promise<string> => {
        const bridge = getPywebviewApi();
        if (bridge?.capture_hotkey) return bridge.capture_hotkey(timeout);
        return '';
    },

    checkHotkeyConflict: async (hotkey: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.check_hotkey_conflict) return bridge.check_hotkey_conflict(hotkey);
        return false;
    },

    getQuickCommands: async (): Promise<QuickCommand[]> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_quick_commands) return bridge.get_quick_commands();
        return [];
    },

    runQuickCommand: async (commandId: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.run_quick_command) return bridge.run_quick_command(commandId);
        return false;
    },

    notifyTray: async (title: string, message: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.notify_tray) return bridge.notify_tray(title, message);
        return false;
    },

    logLocalAction: async (requestText: string, responseText: string): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.log_local_action) return bridge.log_local_action(requestText, responseText);
        return false;
    },

    minimizeToTray: async (): Promise<void> => {
        const bridge = getPywebviewApi();
        if (bridge?.minimize_to_tray) await bridge.minimize_to_tray();
    },

    maximizeWindow: async (): Promise<void> => {
        const bridge = getPywebviewApi();
        if (bridge?.maximize_window) await bridge.maximize_window();
    },

    closeApp: async (): Promise<void> => {
        const bridge = getPywebviewApi();
        if (bridge?.close_app) await bridge.close_app();
    },

    exitApp: async (): Promise<void> => {
        const bridge = getPywebviewApi();
        if (bridge?.exit_app) await bridge.exit_app();
    },

    toggleMiniMode: async (enable: boolean): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.toggle_mini_mode) return bridge.toggle_mini_mode(enable);
        return false;
    },

    pauseApp: async (paused: boolean): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.pause_app) return bridge.pause_app(paused);
        return false;
    },

    restartApp: async (): Promise<boolean> => {
        const bridge = getPywebviewApi();
        if (bridge?.restart_app) return bridge.restart_app();
        return false;
    },

    navigateTo: async (path: string): Promise<void> => {
        const bridge = getPywebviewApi();
        if (bridge?.navigate_to) await bridge.navigate_to(path);
    },

    getShortcuts: async (): Promise<ShortcutsConfig> => {
        const cfg = await api.getConfig();
        return {
            hotkey: cfg.hotkey || 'CTRL+SHIFT+H',
            mute_hotkey: cfg.mute_hotkey || '',
            pause_hotkey: cfg.pause_hotkey || '',
        };
    },

    updateShortcuts: async (shortcuts: ShortcutsConfig): Promise<boolean> => {
        return api.updateConfig(shortcuts);
    },

    getRuntimeState: async (): Promise<RuntimeState | null> => {
        const bridge = getPywebviewApi();
        if (bridge?.get_runtime_state) return bridge.get_runtime_state();
        return null;
    },
};
