import React from 'react';

type SectionHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
};

/**
 * Page-level section header. Used at the top of full pages (Voice, Hermes,
 * Settings, Shortcuts, Commands, TTS). Establishes a single visual rhythm:
 *   eyebrow (mono caps) → display title (large) → description (secondary)
 * with a right-aligned action slot.
 */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  eyebrow,
  title,
  description,
  action,
}) => {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        <p className="eyebrow eyebrow-accent text-[10px]">{eyebrow}</p>
        <h1 className="mt-1.5 font-display text-[28px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-[13px] font-medium leading-relaxed text-[var(--text-secondary)]">
            {description}
          </p>
        )}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
};
