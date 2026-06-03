import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';

type Language = 'en' | 'es';

interface LanguageContextType {
  language: Language;
  toggleLanguage: () => void;
  t: (key: string, vars?: Record<string, string | number> | string) => string;
}

const translations = {
  en: {
    'nav.general': 'Overview',
    'nav.sessions': 'Sessions',
    'nav.history': 'History',
    'nav.notifications': 'Notifications',
    'nav.voice': 'Voice',
    'nav.shortcuts': 'Shortcuts',
    'nav.commands': 'Commands',
    'nav.hermes': 'Hermes',
    'nav.tts': 'TTS',
    'nav.settings': 'Settings',
    'nav.exit': 'Exit',
    'theme.toggle': 'Toggle Theme',
    'lang.toggle': 'Toggle Language',
    'Logout': 'Log Out',
    
    // Home
    'home.ready': 'Hermes is ready',
    'home.instruction': 'Press {hotkey} or say your wake phrase to start talking.',
    'home.connection': 'Connection',
    'home.connected': 'Connected',
    'home.offline': 'Offline',
    'home.quick_controls': 'Quick Controls',
    'home.tts_voice': 'TTS Voice',
    'home.autostart': 'Autostart',
    'home.recent_activity': 'Recent Activity',
    'home.no_messages': 'No recent messages.',
    'home.system_profile': 'System Profile',
    'home.stt_model': 'STT Model',
    'home.wake_words': 'Wake Words Active',
    'home.audio_device': 'Audio Device',
    'home.default_mic': 'System Default Microphone',
    'home.pause': 'Pause',
    'home.resume': 'Resume',
    'home.restart': 'Restart',
    'home.you': 'You',

    // Sessions
    'sessions.eyebrow': 'Conversation Workspace',
    'sessions.title': 'Sessions',
    'sessions.description': 'Switch chats, review message history, and export active conversations.',
    'sessions.remote_id': 'Remote ID:',
    'sessions.copied': 'ID copied to clipboard',
    'sessions.new_session': 'New Session',
    'sessions.chat_history': 'Chat History',
    'sessions.no_messages': 'No messages yet. Send a message to start.',
    'sessions.type_message': 'Type a message manually...',
    'sessions.error_sending': 'Error sending message',
    'sessions.latency': '{ms}ms latency',

    // History
    'history.eyebrow': 'Flight Recorder',
    'history.title': 'Activity Ledger',
    'history.description': 'Recent voice transcriptions and executed actions from this app session.',
    'history.event_count': 'Last {count} events',

    // Notifications
    'notifications.eyebrow': 'Alert Surface',
    'notifications.title': 'Notifications',
    'notifications.description': 'Control overlay feedback and native desktop notices for voice turns and errors.',
    'notifications.overlay_eyebrow': 'Visual Feedback',
    'notifications.overlay_title': 'Overlay Feedback',
    'notifications.overlay_desc': 'Show a small non-invasive overlay during listening, transcribing, and responding.',
    'notifications.overlay_toggle': 'Show overlay feedback',
    'notifications.desktop_eyebrow': 'System Alerts',
    'notifications.desktop_title': 'Desktop Notifications',
    'notifications.desktop_desc': 'Native notices for errors, reconnects, and completed voice turns.',
    'notifications.desktop_toggle': 'Desktop notifications',
    'notifications.save': 'Save Changes',
    'notifications.success': 'Notification settings saved',
    'notifications.error': 'Failed to save notification settings',

    // Settings
    'settings.autostart': 'Autostart',
    'settings.autostart_desc': 'Launch Hermes when Windows starts.',
    'settings.minimize': 'Minimize to Tray',
    'settings.minimize_desc': 'Keep running in the background when closed.',
    'settings.vad_title': 'Voice Activity Detection',
    'settings.vad_wake': 'Wake Sensitivity',
    'settings.vad_silence': 'Silence Threshold',
    'settings.vad_timeout': 'Silence Timeout (s)',
    'settings.save': 'Save Changes',
    'settings.success': 'Settings saved successfully',
    'settings.error': 'Failed to save settings',

    // Voice
    'voice.input': 'Input Device',
    'voice.input_desc': 'Select the microphone for voice capture.',
    'voice.default': 'Default System Device',
    'voice.wake': 'Wake Phrases',
    'voice.wake_desc': 'Comma separated list of phrases to trigger recording.',
    'voice.save': 'Save Changes',
    'voice.success': 'Voice configuration saved',
    'voice.error': 'Failed to save voice configuration',

    // Hermes
    'hermes.url': 'VPS Base URL',
    'hermes.url_desc': 'The endpoint to your Hermes VPS server.',
    'hermes.token': 'API Token / Client Key',
    'hermes.token_desc': 'Used to authenticate requests (Bearer Token or Client Key).',
    'hermes.test': 'Test Connection',
    'hermes.testing': 'Testing...',
    'hermes.save': 'Save Changes',
    'hermes.success': 'Hermes server configuration saved',
    'hermes.error': 'Failed to save Hermes configuration',
    'hermes.test_success': 'Connection successful! Server is healthy.',
    'hermes.test_fail': 'Connection failed. Server returned error.',
    'hermes.test_fatal': 'Connection failed completely. Check URL and Token.',

    // Shortcuts
    'shortcuts.hotkey': 'Activation Hotkey',
    'shortcuts.hotkey_desc': 'Press this combination to start talking.',
    'shortcuts.save': 'Save Changes',
    'shortcuts.success': 'Shortcuts saved successfully',
    'shortcuts.error': 'Failed to save shortcuts',

    // Commands
    'commands.title': 'Custom Commands',
    'commands.description': 'Create local voice shortcuts that trigger apps, searches, hotkeys, volume changes, or speech.',
    'commands.new': 'New Command',
    'commands.library': 'Command Library',
    'commands.count_suffix': 'configured',
    'commands.loading': 'Loading commands...',
    'commands.empty_title': 'No commands yet',
    'commands.empty_desc': 'Add a command to map trigger phrases to one or more desktop actions.',
    'commands.actions': 'actions',
    'commands.test': 'Test',
    'commands.testing': 'Testing',
    'commands.edit': 'Edit',
    'commands.delete': 'Delete',
    'commands.edit_title': 'Edit Command',
    'commands.create_title': 'New Command',
    'commands.form_desc': 'Define the phrases Hermes should recognize and the actions to run.',
    'commands.close': 'Close',
    'commands.name': 'Name',
    'commands.name_placeholder': 'Open my editor',
    'commands.triggers': 'Trigger phrases',
    'commands.triggers_placeholder': 'open code, start editor',
    'commands.triggers_hint': 'Separate phrases with commas.',
    'commands.action_list': 'Actions',
    'commands.add_action': 'Add Action',
    'commands.target_placeholder': 'Target, phrase, hotkey, or value',
    'commands.remove_action': 'Remove action',
    'commands.cancel': 'Cancel',
    'commands.save': 'Save Command',
    'commands.saving': 'Saving...',
    'commands.load_error': 'Failed to load custom commands',
    'commands.validation_error': 'Add a name, at least one trigger phrase, and one complete action',
    'commands.create_success': 'Command created',
    'commands.update_success': 'Command updated',
    'commands.save_error': 'Failed to save command',
    'commands.delete_confirm': 'Delete this command?',
    'commands.delete_success': 'Command deleted',
    'commands.delete_error': 'Failed to delete command',
    'commands.test_success': 'Command test sent',
    'commands.test_error': 'Failed to test command',

    // TTS
    'tts.feedback': 'Feedback Mode',
    'tts.feedback_desc': 'How Hermes responds to you.',
    'tts.both': 'Voice and Beeps',
    'tts.voice': 'Voice Only',
    'tts.beep': 'Beeps Only',
    'tts.off': 'Silent',
    'tts.save': 'Save Changes',
    'tts.success': 'TTS configuration saved',
    'tts.error': 'Failed to save TTS settings'
  },
  es: {
    'nav.general': 'Resumen',
    'nav.sessions': 'Sesiones',
    'nav.history': 'Historial',
    'nav.notifications': 'Notificaciones',
    'nav.voice': 'Voz',
    'nav.shortcuts': 'Atajos',
    'nav.commands': 'Comandos',
    'nav.hermes': 'Hermes',
    'nav.tts': 'Síntesis de Voz',
    'nav.settings': 'Ajustes',
    'theme.toggle': 'Cambiar Tema',
    'lang.toggle': 'Cambiar Idioma',
    'Logout': 'Cerrar Sesión',
    
    // Home
    'home.ready': 'Hermes está listo',
    'home.instruction': 'Presiona {hotkey} o di tu frase mágica para empezar a hablar.',
    'home.connection': 'Conexión',
    'home.connected': 'Conectado',
    'home.offline': 'Desconectado',
    'home.quick_controls': 'Controles Rápidos',
    'home.tts_voice': 'Voz TTS',
    'home.autostart': 'Inicio Automático',
    'home.recent_activity': 'Actividad Reciente',
    'home.no_messages': 'No hay mensajes recientes.',
    'home.system_profile': 'Perfil del Sistema',
    'home.stt_model': 'Modelo STT',
    'home.wake_words': 'Palabras Mágicas Activas',
    'home.audio_device': 'Dispositivo de Audio',
    'home.default_mic': 'Micrófono por Defecto del Sistema',
    'home.pause': 'Pausar',
    'home.resume': 'Reanudar',
    'home.restart': 'Reiniciar',
    'home.you': 'Tú',

    // Sessions
    'sessions.eyebrow': 'Espacio de Conversación',
    'sessions.title': 'Sesiones',
    'sessions.description': 'Cambia de chat, revisa el historial de mensajes y exporta conversaciones activas.',
    'sessions.remote_id': 'ID Remoto:',
    'sessions.copied': 'ID copiado al portapapeles',
    'sessions.new_session': 'Nueva Sesión',
    'sessions.chat_history': 'Historial de Chat',
    'sessions.no_messages': 'Aún no hay mensajes. Envía uno para empezar.',
    'sessions.type_message': 'Escribe un mensaje manualmente...',
    'sessions.error_sending': 'Error al enviar el mensaje',
    'sessions.latency': '{ms}ms de latencia',

    // History
    'history.eyebrow': 'Registro de Vuelo',
    'history.title': 'Historial de Actividad',
    'history.description': 'Transcripciones recientes y acciones ejecutadas en esta sesión de la app.',
    'history.event_count': 'Últimos {count} eventos',

    // Notifications
    'notifications.eyebrow': 'Superficie de Alertas',
    'notifications.title': 'Notificaciones',
    'notifications.description': 'Controla el overlay visual y los avisos nativos de escritorio para turnos de voz y errores.',
    'notifications.overlay_eyebrow': 'Feedback Visual',
    'notifications.overlay_title': 'Overlay de Feedback',
    'notifications.overlay_desc': 'Muestra un overlay pequeño y no invasivo durante escucha, transcripción y respuesta.',
    'notifications.overlay_toggle': 'Mostrar overlay de feedback',
    'notifications.desktop_eyebrow': 'Alertas del Sistema',
    'notifications.desktop_title': 'Notificaciones de Escritorio',
    'notifications.desktop_desc': 'Avisos nativos para errores, reconexiones y turnos de voz completados.',
    'notifications.desktop_toggle': 'Notificaciones de escritorio',
    'notifications.save': 'Guardar Cambios',
    'notifications.success': 'Ajustes de notificaciones guardados',
    'notifications.error': 'Error al guardar ajustes de notificaciones',

    // Settings
    'settings.autostart': 'Inicio Automático',
    'settings.autostart_desc': 'Inicia Hermes al arrancar Windows.',
    'settings.minimize': 'Minimizar a la Bandeja',
    'settings.minimize_desc': 'Sigue funcionando en segundo plano al cerrar.',
    'settings.vad_title': 'Detección de Voz (VAD)',
    'settings.vad_wake': 'Sensibilidad de Activación',
    'settings.vad_silence': 'Umbral de Silencio',
    'settings.vad_timeout': 'Tiempo de Silencio (s)',
    'settings.save': 'Guardar Cambios',
    'settings.success': 'Ajustes guardados correctamente',
    'settings.error': 'Error al guardar ajustes',

    // Voice
    'voice.input': 'Dispositivo de Entrada',
    'voice.input_desc': 'Selecciona el micrófono para captura de voz.',
    'voice.default': 'Dispositivo del Sistema',
    'voice.wake': 'Frases Mágicas',
    'voice.wake_desc': 'Lista de frases separadas por comas para iniciar la grabación.',
    'voice.save': 'Guardar Cambios',
    'voice.success': 'Configuración de voz guardada',
    'voice.error': 'Error al guardar configuración de voz',

    // Hermes
    'hermes.url': 'URL Base del VPS',
    'hermes.url_desc': 'La dirección de tu servidor VPS Hermes.',
    'hermes.token': 'Token API / Clave Cliente',
    'hermes.token_desc': 'Usado para autenticar peticiones.',
    'hermes.test': 'Probar Conexión',
    'hermes.testing': 'Probando...',
    'hermes.save': 'Guardar Cambios',
    'hermes.success': 'Configuración del servidor guardada',
    'hermes.error': 'Error al guardar configuración del servidor',
    'hermes.test_success': '¡Conexión exitosa! El servidor responde.',
    'hermes.test_fail': 'La conexión falló. El servidor devolvió un error.',
    'hermes.test_fatal': 'Error de conexión total. Comprueba la URL y el Token.',

    // Shortcuts
    'shortcuts.hotkey': 'Atajo de Activación',
    'shortcuts.hotkey_desc': 'Presiona esta combinación para empezar a hablar.',
    'shortcuts.save': 'Guardar Cambios',
    'shortcuts.success': 'Atajos guardados correctamente',
    'shortcuts.error': 'Error al guardar atajos',

    // Commands
    'commands.title': 'Comandos Personalizados',
    'commands.description': 'Crea atajos de voz locales que abren apps, buscan en la web, ejecutan hotkeys, cambian volumen o hablan.',
    'commands.new': 'Nuevo Comando',
    'commands.library': 'Biblioteca de Comandos',
    'commands.count_suffix': 'configurados',
    'commands.loading': 'Cargando comandos...',
    'commands.empty_title': 'Aún no hay comandos',
    'commands.empty_desc': 'Agrega un comando para asociar frases de activación con una o más acciones de escritorio.',
    'commands.actions': 'acciones',
    'commands.test': 'Probar',
    'commands.testing': 'Probando',
    'commands.edit': 'Editar',
    'commands.delete': 'Eliminar',
    'commands.edit_title': 'Editar Comando',
    'commands.create_title': 'Nuevo Comando',
    'commands.form_desc': 'Define las frases que Hermes debe reconocer y las acciones que ejecutará.',
    'commands.close': 'Cerrar',
    'commands.name': 'Nombre',
    'commands.name_placeholder': 'Abrir mi editor',
    'commands.triggers': 'Frases de activación',
    'commands.triggers_placeholder': 'abre código, inicia editor',
    'commands.triggers_hint': 'Separa las frases con comas.',
    'commands.action_list': 'Acciones',
    'commands.add_action': 'Agregar Acción',
    'commands.target_placeholder': 'Destino, frase, hotkey o valor',
    'commands.remove_action': 'Quitar acción',
    'commands.cancel': 'Cancelar',
    'commands.save': 'Guardar Comando',
    'commands.saving': 'Guardando...',
    'commands.load_error': 'Error al cargar comandos personalizados',
    'commands.validation_error': 'Agrega un nombre, al menos una frase de activación y una acción completa',
    'commands.create_success': 'Comando creado',
    'commands.update_success': 'Comando actualizado',
    'commands.save_error': 'Error al guardar comando',
    'commands.delete_confirm': '¿Eliminar este comando?',
    'commands.delete_success': 'Comando eliminado',
    'commands.delete_error': 'Error al eliminar comando',
    'commands.test_success': 'Prueba de comando enviada',
    'commands.test_error': 'Error al probar comando',

    // TTS
    'tts.feedback': 'Modo de Respuesta',
    'tts.feedback_desc': 'Cómo Hermes te responde.',
    'tts.both': 'Voz y Pitidos',
    'tts.voice': 'Solo Voz',
    'tts.beep': 'Solo Pitidos',
    'tts.off': 'Silencio',
    'tts.save': 'Guardar Cambios',
    'tts.success': 'Configuración de TTS guardada',
    'tts.error': 'Error al guardar configuración de TTS'
  }
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>('en');

  useEffect(() => {
    api.getConfig().then(config => {
      if (config.language === 'es' || config.language === 'en') {
        setLanguage(config.language);
      }
    });
  }, []);

  const toggleLanguage = async () => {
    const newLang = language === 'en' ? 'es' : 'en';
    setLanguage(newLang);
    await api.updateConfig({ language: newLang });
  };

  const t = (key: string, vars?: Record<string, string | number> | string) => {
    let str = (translations[language] as any)[key] || (typeof vars === 'string' ? vars : key);
    if (typeof vars === 'string') return str;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(`{${k}}`, String(v));
      }
    }
    return str;
  };

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
};
