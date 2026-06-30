import React from 'react';

type PageHeaderProps = {
  title: string;
  caption?: string;
  description?: string;
  action?: React.ReactNode;
};

/** Single page title — shown once per route (not duplicated in titlebar). */
export const PageHeader: React.FC<PageHeaderProps> = ({ title, caption, description, action }) => {
  return (
    <header className="ds-page-header">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          {caption ? <p className="ds-caption mb-1">{caption}</p> : null}
          <h1 className="ds-page-title">{title}</h1>
          {description ? <p className="ds-page-desc mt-1">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </header>
  );
};

/** @deprecated Use PageHeader */
export const SectionHeader = PageHeader;
