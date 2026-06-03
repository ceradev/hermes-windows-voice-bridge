import React from 'react';

type SectionHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
};

/** Same block used in Shortcuts, TTS and Commands page intros. */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  eyebrow,
  title,
  description,
  action,
}) => {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">
          {eyebrow}
        </p>
        <h3 className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{title}</h3>
        <p className="mt-2 text-sm font-medium text-gray-500 dark:text-gray-400">{description}</p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
};
