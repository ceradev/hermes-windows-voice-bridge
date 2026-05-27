import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Play, X, Terminal, ListPlus } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useLanguage } from '../contexts/LanguageContext';
import type { CustomCommand, CustomCommandAction } from '../types';

const actionTypes = ['open_app', 'web_search', 'system_volume', 'tts_speak', 'hotkey'];

type CommandFormState = {
  name: string;
  triggerPhrases: string;
  actions: CustomCommandAction[];
};

const createEmptyAction = (): CustomCommandAction => ({
  type: 'open_app',
  target: '',
});

const createEmptyForm = (): CommandFormState => ({
  name: '',
  triggerPhrases: '',
  actions: [createEmptyAction()],
});

const formatStep = (index: number) => String(index + 1).padStart(2, '0');

export const Commands = () => {
  const [commands, setCommands] = useState<CustomCommand[]>([]);
  const [form, setForm] = useState<CommandFormState>(createEmptyForm);
  const [editingCommand, setEditingCommand] = useState<CustomCommand | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const { success, error } = useToast();
  const { t } = useLanguage();

  const label = (key: string, fallback: string) => {
    const translated = t(key);
    return translated === key ? fallback : translated;
  };

  const loadCommands = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await api.getCustomCommands();
      setCommands(Array.isArray(list) ? list : []);
    } catch (e) {
      error(label('commands.load_error', 'Failed to load custom commands'));
    } finally {
      setIsLoading(false);
    }
  }, [error, t]);

  useEffect(() => {
    loadCommands();
  }, [loadCommands]);

  const openCreateModal = () => {
    setEditingCommand(null);
    setForm(createEmptyForm());
    setIsModalOpen(true);
  };

  const openEditModal = (command: CustomCommand) => {
    setEditingCommand(command);
    setForm({
      name: command.name,
      triggerPhrases: command.trigger_phrases.join(', '),
      actions: command.actions.length > 0 ? command.actions : [createEmptyAction()],
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (isSaving) return;
    setIsModalOpen(false);
    setEditingCommand(null);
    setForm(createEmptyForm());
  };

  const resetModal = () => {
    setIsModalOpen(false);
    setEditingCommand(null);
    setForm(createEmptyForm());
  };

  const updateAction = (index: number, updates: Partial<CustomCommandAction>) => {
    setForm((prev) => ({
      ...prev,
      actions: prev.actions.map((action, actionIndex) => (
        actionIndex === index ? { ...action, ...updates } : action
      )),
    }));
  };

  const addAction = () => {
    setForm((prev) => ({
      ...prev,
      actions: [...prev.actions, createEmptyAction()],
    }));
  };

  const removeAction = (index: number) => {
    setForm((prev) => ({
      ...prev,
      actions: prev.actions.length === 1
        ? prev.actions
        : prev.actions.filter((_, actionIndex) => actionIndex !== index),
    }));
  };

  const buildPayload = () => {
    const triggerPhrases = form.triggerPhrases
      .split(',')
      .map((phrase) => phrase.trim())
      .filter(Boolean);

    const actions = form.actions
      .map((action) => ({
        type: action.type,
        target: action.target.trim(),
      }))
      .filter((action) => action.type && action.target);

    return {
      name: form.name.trim(),
      trigger_phrases: triggerPhrases,
      actions,
    };
  };

  const handleSave = async () => {
    const payload = buildPayload();

    if (!payload.name || payload.trigger_phrases.length === 0 || payload.actions.length === 0) {
      error(label('commands.validation_error', 'Add a name, at least one trigger phrase, and one complete action'));
      return;
    }

    setIsSaving(true);
    try {
      let saved = false;
      if (editingCommand) {
        saved = await api.updateCustomCommand(editingCommand.id, payload);
        if (!saved) throw new Error('update_custom_command returned false');
        success(label('commands.update_success', 'Command updated'));
      } else {
        saved = await api.addCustomCommand(payload);
        if (!saved) throw new Error('add_custom_command returned false');
        success(label('commands.create_success', 'Command created'));
      }
      resetModal();
      await loadCommands();
    } catch (e) {
      error(label('commands.save_error', 'Failed to save command'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (command: CustomCommand) => {
    const confirmed = window.confirm(label('commands.delete_confirm', `Delete "${command.name}"?`));
    if (!confirmed) return;

    try {
      const deleted = await api.deleteCustomCommand(command.id);
      if (!deleted) throw new Error('delete_custom_command returned false');
      success(label('commands.delete_success', 'Command deleted'));
      await loadCommands();
    } catch (e) {
      error(label('commands.delete_error', 'Failed to delete command'));
    }
  };

  const handleTest = async (command: CustomCommand) => {
    setTestingId(command.id);
    try {
      const tested = await api.testCustomCommand(command.id);
      if (!tested) throw new Error('test_custom_command returned false');
      success(label('commands.test_success', 'Command test sent'));
    } catch (e) {
      error(label('commands.test_error', 'Failed to test command'));
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 flex h-full flex-col duration-500">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">IF voice phrase THEN action chain</p>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-control)] border border-black/10 bg-black/5 text-gray-900 dark:border-white/10 dark:bg-white/10 dark:text-white">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-3xl font-extrabold uppercase tracking-tighter text-gray-900 dark:text-white">
                {label('commands.title', 'Custom Commands')}
              </h3>
              <p className="mt-1 text-sm font-semibold text-gray-500 dark:text-gray-400">
                {label('commands.description', 'Create local voice shortcuts that trigger apps, searches, hotkeys, volume changes, or speech.')}
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center justify-center gap-2 rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-5 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-gray-900 shadow-lg backdrop-blur-md transition-colors hover:bg-black/10 dark:border-white/20 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
        >
          <Plus size={16} /> {label('commands.new', 'New Command')}
        </button>
      </div>

      <div className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-panel)] transition-all duration-300">
        <div className="flex shrink-0 items-center justify-between border-b border-black/10 p-5 dark:border-white/10">
          <div>
            <h4 className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">
              {label('commands.library', 'Command Library')}
            </h4>
            <p className="mt-1 font-mono text-xs font-bold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
              {commands.length} {label('commands.count_suffix', 'configured')}
            </p>
          </div>
        </div>

        <div className="custom-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto p-4 pb-20">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center font-mono text-xs font-bold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
              {label('commands.loading', 'Loading commands...')}
            </div>
          ) : commands.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-[var(--radius-control)] border border-black/10 bg-black/5 text-gray-500 dark:border-white/10 dark:bg-white/10 dark:text-gray-400">
                <ListPlus className="h-6 w-6" />
              </div>
              <h4 className="mb-1 font-bold text-gray-900 dark:text-white">
                {label('commands.empty_title', 'No commands yet')}
              </h4>
              <p className="max-w-sm text-sm font-semibold text-gray-500 dark:text-gray-400">
                {label('commands.empty_desc', 'Add a command to map trigger phrases to one or more desktop actions.')}
              </p>
            </div>
          ) : (
            commands.map((command) => (
              <div
                key={command.id}
                className="group grid grid-cols-1 gap-4 rounded-[var(--radius-panel)] border border-black/10 bg-black/5 p-4 transition-colors hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 lg:grid-cols-[220px_1fr_auto]"
              >
                <div className="min-w-0 border-b border-black/10 pb-4 dark:border-white/10 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-4">
                  <p className="mb-2 font-mono text-[10px] font-extrabold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">IF</p>
                  <h4 className="mb-3 truncate text-base font-extrabold text-gray-900 dark:text-white">{command.name}</h4>
                  <div className="flex flex-wrap gap-2">
                    {command.trigger_phrases.map((phrase, index) => (
                      <span
                        key={`${phrase}-${index}`}
                        className="border border-black/10 bg-white/70 px-2.5 py-1.5 font-mono text-[11px] font-bold text-gray-800 shadow-inner dark:border-white/10 dark:bg-black/30 dark:text-gray-200"
                      >
                        {phrase}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">THEN</p>
                    <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
                      {command.actions.length} {label('commands.actions', 'actions')}
                    </span>
                  </div>
                  <div className="relative space-y-3 pl-9 before:absolute before:left-[13px] before:top-3 before:bottom-3 before:w-px before:bg-black/15 dark:before:bg-white/15">
                    {command.actions.map((action, index) => (
                      <div key={`${action.type}-${index}`} className="relative rounded-[var(--radius-control)] border border-black/10 bg-white/60 px-3 py-2 shadow-inner dark:border-white/10 dark:bg-black/20">
                        <span className="absolute -left-9 top-2 flex h-7 w-7 items-center justify-center border border-black/10 bg-white font-mono text-[10px] font-extrabold text-gray-700 dark:border-white/10 dark:bg-gray-950 dark:text-gray-200">
                          {formatStep(index)}
                        </span>
                        <p className="font-mono text-[10px] font-extrabold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">{action.type}</p>
                        <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-200">{action.target}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2 lg:flex-col lg:items-end lg:opacity-80 lg:transition-opacity lg:group-hover:opacity-100">
                  <button
                    onClick={() => handleTest(command)}
                    disabled={testingId === command.id}
                    aria-label={label('commands.test', 'Test')}
                    className="flex items-center gap-2 rounded-[var(--radius-control)] border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 font-mono text-xs font-bold uppercase tracking-[0.12em] text-emerald-700 transition-colors hover:bg-emerald-500/20 disabled:opacity-60 dark:text-emerald-300"
                  >
                    <Play size={14} className={testingId === command.id ? 'animate-pulse' : ''} />
                    {testingId === command.id ? label('commands.testing', 'Testing') : label('commands.test', 'Test')}
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={() => openEditModal(command)}
                      aria-label={label('commands.edit', 'Edit')}
                      className="rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-2.5 text-gray-700 transition-colors hover:bg-black/10 dark:border-white/10 dark:bg-white/10 dark:text-gray-300 dark:hover:bg-white/20"
                      title={label('commands.edit', 'Edit')}
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => handleDelete(command)}
                      aria-label={label('commands.delete', 'Delete')}
                      className="rounded-[var(--radius-control)] border border-red-500/20 bg-red-500/10 p-2.5 text-red-600 transition-colors hover:bg-red-500/20 dark:text-red-400"
                      title={label('commands.delete', 'Delete')}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-panel flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-[var(--radius-panel)] shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="commands-dialog-title">
            <div className="flex items-start justify-between gap-4 border-b border-black/10 p-6 dark:border-white/10">
              <div>
                <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Command Chain Editor</p>
                <h3 id="commands-dialog-title" className="text-2xl font-extrabold uppercase tracking-tighter text-gray-900 dark:text-white">
                  {editingCommand ? label('commands.edit_title', 'Edit Command') : label('commands.create_title', 'New Command')}
                </h3>
                <p className="mt-1 text-sm font-semibold text-gray-500 dark:text-gray-400">
                  {label('commands.form_desc', 'Define the phrases Hermes should recognize and the actions to run.')}
                </p>
              </div>
              <button
                onClick={closeModal}
                aria-label={label('commands.close', 'Close')}
                className="rounded-[var(--radius-control)] p-2 text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 dark:hover:bg-white/10 dark:hover:text-white"
                title={label('commands.close', 'Close')}
              >
                <X size={20} />
              </button>
            </div>

            <div className="custom-scrollbar overflow-y-auto p-6">
              <div className="mb-5">
                <label className="mb-2 block font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-gray-600 dark:text-gray-400">
                  {label('commands.name', 'Name')}
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-4 text-sm font-semibold text-gray-900 transition-colors focus:border-gray-900 focus:outline-none dark:border-white/10 dark:bg-[#0a0a0a] dark:text-white dark:focus:border-white"
                  placeholder={label('commands.name_placeholder', 'Open my editor')}
                />
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.85fr_1.15fr]">
                <section className="rounded-[var(--radius-panel)] border border-black/10 bg-black/5 p-4 dark:border-white/10 dark:bg-white/5">
                  <div className="mb-3 flex items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
                    <label className="font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-gray-600 dark:text-gray-400">
                      IF trigger phrases
                    </label>
                    <span className="font-mono text-[10px] font-bold text-gray-500">VOC</span>
                  </div>
                  <input
                    type="text"
                    value={form.triggerPhrases}
                    onChange={(e) => setForm((prev) => ({ ...prev, triggerPhrases: e.target.value }))}
                    className="w-full rounded-[var(--radius-control)] border border-black/10 bg-white/70 p-4 font-mono text-sm font-semibold text-gray-900 transition-colors focus:border-gray-900 focus:outline-none dark:border-white/10 dark:bg-[#0a0a0a] dark:text-white dark:focus:border-white"
                    placeholder={label('commands.triggers_placeholder', 'open code, start editor')}
                  />
                  <p className="mt-3 text-xs font-semibold text-gray-500 dark:text-gray-400">
                    {label('commands.triggers_hint', 'Separate phrases with commas.')}
                  </p>
                </section>

                <section className="rounded-[var(--radius-panel)] border border-black/10 bg-black/5 p-4 dark:border-white/10 dark:bg-white/5">
                  <div className="mb-3 flex items-center justify-between gap-4 border-b border-black/10 pb-3 dark:border-white/10">
                    <label className="font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-gray-600 dark:text-gray-400">
                      THEN action chain
                    </label>
                    <button
                      onClick={addAction}
                      className="flex items-center gap-2 rounded-[var(--radius-control)] border border-black/10 bg-white/70 px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-gray-900 transition-colors hover:bg-white dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
                    >
                      <Plus size={14} /> {label('commands.add_action', 'Add Action')}
                    </button>
                  </div>

                  <div className="relative space-y-3 pl-9 before:absolute before:left-[13px] before:top-3 before:bottom-3 before:w-px before:bg-black/15 dark:before:bg-white/15">
                    {form.actions.map((action, index) => (
                      <div
                        key={index}
                        className="relative grid grid-cols-1 gap-3 rounded-[var(--radius-control)] border border-black/10 bg-white/70 p-3 dark:border-white/10 dark:bg-black/20 md:grid-cols-[180px_1fr_auto]"
                      >
                        <span className="absolute -left-9 top-3 flex h-7 w-7 items-center justify-center border border-black/10 bg-white font-mono text-[10px] font-extrabold text-gray-700 dark:border-white/10 dark:bg-gray-950 dark:text-gray-200">
                          {formatStep(index)}
                        </span>
                        <select
                          value={action.type}
                          onChange={(e) => updateAction(index, { type: e.target.value })}
                          className="w-full rounded-[var(--radius-control)] border border-black/10 bg-white p-3 font-mono text-xs font-bold text-gray-900 transition-colors focus:border-gray-900 focus:outline-none dark:border-white/10 dark:bg-[#0a0a0a] dark:text-white dark:focus:border-white"
                        >
                          {actionTypes.map((actionType) => (
                            <option key={actionType} value={actionType}>{actionType}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={action.target}
                          onChange={(e) => updateAction(index, { target: e.target.value })}
                          className="w-full rounded-[var(--radius-control)] border border-black/10 bg-white p-3 text-sm font-semibold text-gray-900 transition-colors focus:border-gray-900 focus:outline-none dark:border-white/10 dark:bg-[#0a0a0a] dark:text-white dark:focus:border-white"
                          placeholder={label('commands.target_placeholder', 'Target, phrase, hotkey, or value')}
                        />
                        <button
                          onClick={() => removeAction(index)}
                          disabled={form.actions.length === 1}
                          aria-label={label('commands.remove_action', 'Remove action')}
                          className="rounded-[var(--radius-control)] border border-red-500/20 bg-red-500/10 p-3 text-red-600 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-40 dark:text-red-400"
                          title={label('commands.remove_action', 'Remove action')}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-black/10 bg-white/50 p-6 backdrop-blur-xl dark:border-white/10 dark:bg-black/20">
              <button
                onClick={closeModal}
                disabled={isSaving}
                className="rounded-[var(--radius-control)] bg-gray-100 px-5 py-3 font-mono text-xs font-bold uppercase tracking-[0.12em] text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-60 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {label('commands.cancel', 'Cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="rounded-[var(--radius-control)] bg-gray-950 px-6 py-3 font-mono text-xs font-bold uppercase tracking-[0.12em] text-white shadow-lg transition-colors hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-gray-950 dark:hover:bg-gray-200"
              >
                {isSaving ? label('commands.saving', 'Saving...') : label('commands.save', 'Save Command')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
