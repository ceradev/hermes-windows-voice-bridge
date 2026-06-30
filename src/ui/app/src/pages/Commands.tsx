import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Play, X, Terminal, ListPlus } from 'lucide-react';
import { PageHeader } from '../components/Layout/PageHeader';
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
      if (editingCommand) {
        const saved = await api.updateCustomCommand(editingCommand.id, payload);
        if (!saved) throw new Error('update_custom_command returned false');
        success(label('commands.update_success', 'Command updated'));
      } else {
        const result = await api.addCustomCommand(payload);
        if (!result?.id) throw new Error('add_custom_command returned no id');
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
    <div className="flex h-full flex-col">
      <PageHeader
        title={label('commands.title', 'Custom commands')}
        description={`${label('commands.description', 'Create local voice shortcuts that trigger apps, searches, hotkeys, volume changes, or speech.')}${commands.length > 0 ? ` · ${commands.length} ${label('commands.count_suffix', 'configured')}` : ''}`}
        action={
          <button
            onClick={openCreateModal}
            className="btn-primary px-4 py-2 text-[15px] font-semibold"
          >
            <Plus size={18} /> {label('commands.new', 'New command')}
          </button>
        }
      />

      <div className="surface-base flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="custom-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto p-4 pb-20">
          {isLoading ? (
            <div className="flex h-64 flex-col gap-4">
              <div className="surface-inset h-[120px] w-full animate-pulse opacity-50" />
              <div className="surface-inset h-[120px] w-full animate-pulse opacity-50" />
              <div className="surface-inset h-[120px] w-full animate-pulse opacity-50" />
            </div>
          ) : commands.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center surface-raised text-[var(--text-muted)]">
                <ListPlus className="h-6 w-6" />
              </div>
              <h4 className="mb-1 text-heading">
                {label('commands.empty_title', 'No commands yet')}
              </h4>
              <p className="max-w-sm text-body text-[var(--text-secondary)]">
                {label('commands.empty_desc', 'Add a command to map trigger phrases to one or more desktop actions.')}
              </p>
            </div>
          ) : (
            commands.map((command) => (
              <div
                key={command.id}
                className="group grid grid-cols-1 gap-4 surface-raised p-4 transition-colors hover:border-[var(--border-strong)] lg:grid-cols-[220px_1fr_auto]"
              >
                <div className="min-w-0 border-b border-[var(--border-subtle)] pb-4 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-4">
                  <p className="mb-2 text-caption text-[var(--text-tertiary)]">If</p>
                  <h4 className="mb-3 truncate text-heading">{command.name}</h4>
                  <div className="flex flex-wrap gap-2">
                    {command.trigger_phrases.map((phrase, index) => (
                      <span
                        key={`${phrase}-${index}`}
                        className="surface-inset px-2.5 py-1 text-body"
                      >
                        {phrase}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="text-caption text-[var(--text-tertiary)]">Then</p>
                    <span className="text-caption text-[var(--text-muted)]">
                      {command.actions.length} {label('commands.actions', 'actions')}
                    </span>
                  </div>
                  <div className="relative space-y-3 pl-9 before:absolute before:left-[13px] before:top-3 before:bottom-3 before:w-px before:bg-[var(--border-subtle)]">
                    {command.actions.map((action, index) => (
                      <div key={`${action.type}-${index}`} className="relative surface-base px-3 py-2">
                        <span className="absolute -left-9 top-2 flex h-7 w-7 items-center justify-center surface-base text-caption text-[var(--text-secondary)]">
                          {formatStep(index)}
                        </span>
                        <p className="text-caption mb-1 text-[var(--text-tertiary)]">{action.type}</p>
                        <p className="truncate text-body text-[var(--text-primary)]">{action.target}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2 lg:flex-col lg:items-end lg:opacity-80 lg:transition-opacity lg:group-hover:opacity-100">
                  <button
                    onClick={() => handleTest(command)}
                    disabled={testingId === command.id}
                    aria-label={label('commands.test', 'Test')}
                    className="btn-base bg-[var(--state-ready)]/10 border-[var(--state-ready)]/20 text-[var(--state-ready)] hover:bg-[var(--state-ready)]/20"
                  >
                    <Play size={14} className={testingId === command.id ? 'animate-pulse' : ''} />
                    {testingId === command.id ? label('commands.testing', 'Testing') : label('commands.test', 'Test')}
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={() => openEditModal(command)}
                      aria-label={label('commands.edit', 'Edit')}
                      className="btn-base px-2.5 py-2.5 text-[var(--text-secondary)]"
                      title={label('commands.edit', 'Edit')}
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => handleDelete(command)}
                      aria-label={label('commands.delete', 'Delete')}
                      className="btn-base px-2.5 py-2.5 bg-[var(--state-error)]/10 border-[var(--state-error)]/20 text-[var(--state-error)] hover:bg-[var(--state-error)]/20"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-5 backdrop-blur-sm">
          <div className="surface-base flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden shadow-card" role="dialog" aria-modal="true" aria-labelledby="commands-dialog-title">
            <div className="flex items-start justify-between gap-4 border-b border-[var(--border-default)] p-5">
              <div>
                <h3 id="commands-dialog-title" className="ds-page-title">
                  {editingCommand ? label('commands.edit_title', 'Edit command') : label('commands.create_title', 'New command')}
                </h3>
                <p className="mt-1 text-body text-[var(--text-secondary)]">
                  {label('commands.form_desc', 'Define the phrases Hermes should recognize and the actions to run.')}
                </p>
              </div>
              <button
                onClick={closeModal}
                aria-label={label('commands.close', 'Close')}
                className="btn-ghost p-2"
                title={label('commands.close', 'Close')}
              >
                <X size={20} />
              </button>
            </div>

            <div className="custom-scrollbar overflow-y-auto p-5">
              <div className="mb-4">
                <label className="ds-label mb-2 block">
                  {label('commands.name', 'Name')}
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="field"
                  placeholder={label('commands.name_placeholder', 'Open my editor')}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[0.85fr_1.15fr]">
                <section className="surface-raised p-4">
                  <div className="mb-3 flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
                    <label className="ds-label">
                      If trigger phrases
                    </label>
                    <span className="text-caption text-[var(--text-muted)]">Voice</span>
                  </div>
                  <input
                    type="text"
                    value={form.triggerPhrases}
                    onChange={(e) => setForm((prev) => ({ ...prev, triggerPhrases: e.target.value }))}
                    className="field"
                    placeholder={label('commands.triggers_placeholder', 'open code, start editor')}
                  />
                  <p className="mt-2 text-caption text-[var(--text-tertiary)]">
                    {label('commands.triggers_hint', 'Separate phrases with commas.')}
                  </p>
                </section>

                <section className="surface-raised p-4">
                  <div className="mb-3 flex items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-3">
                    <label className="ds-label">
                      Then action chain
                    </label>
                    <button
                      onClick={addAction}
                      className="btn-base py-1.5 px-3 text-[14px]"
                    >
                      <Plus size={14} /> {label('commands.add_action', 'Add Action')}
                    </button>
                  </div>

                  <div className="relative space-y-3 pl-9 before:absolute before:left-[13px] before:top-3 before:bottom-3 before:w-px before:bg-[var(--border-subtle)]">
                    {form.actions.map((action, index) => (
                      <div
                        key={index}
                        className="relative grid grid-cols-1 gap-3 surface-inset p-3 md:grid-cols-[180px_1fr_auto]"
                      >
                        <span className="absolute -left-9 top-3 flex h-7 w-7 items-center justify-center surface-base text-caption text-[var(--text-secondary)]">
                          {formatStep(index)}
                        </span>
                        <select
                          value={action.type}
                          onChange={(e) => updateAction(index, { type: e.target.value })}
                          className="field"
                        >
                          {actionTypes.map((actionType) => (
                            <option key={actionType} value={actionType}>{actionType}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={action.target}
                          onChange={(e) => updateAction(index, { target: e.target.value })}
                          className="field"
                          placeholder={label('commands.target_placeholder', 'Target, phrase, hotkey, or value')}
                        />
                        <button
                          onClick={() => removeAction(index)}
                          disabled={form.actions.length === 1}
                          aria-label={label('commands.remove_action', 'Remove action')}
                          className="btn-base px-2.5 py-2.5 bg-[var(--state-error)]/10 border-[var(--state-error)]/20 text-[var(--state-error)] hover:bg-[var(--state-error)]/20 disabled:cursor-not-allowed disabled:opacity-40"
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

            <div className="flex justify-end gap-3 border-t border-[var(--border-default)] bg-[var(--surface-0)] p-5">
              <button
                onClick={closeModal}
                disabled={isSaving}
                className="btn-ghost"
              >
                {label('commands.cancel', 'Cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn-primary"
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
