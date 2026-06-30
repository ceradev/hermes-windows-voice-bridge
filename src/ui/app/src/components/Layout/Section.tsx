import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { SectionTitle } from './SectionTitle';

type SectionProps = {
  title: string;
  icon?: LucideIcon;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

/** Settings-style block: distinct header band + content body. */
export const Section = ({ title, icon, description, action, children, className = '' }: SectionProps) => (
  <section className={`ds-section-block ${className}`.trim()}>
    <header className="ds-section-block__header">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <SectionTitle icon={icon} flush>
            {title}
          </SectionTitle>
          {description ? <p className="ds-section-block__desc">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </header>
    <div className="ds-section-block__body">{children}</div>
  </section>
);

type CardSectionProps = {
  title: string;
  icon?: LucideIcon;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

/** Card with separated header row — for overview / chat panels. */
export const CardSection = ({ title, icon: Icon, action, children, className = '' }: CardSectionProps) => (
  <div className={`ds-card-section ${className}`.trim()}>
    <header className="ds-card-section__header">
      <h2 className="ds-card-section__title">
        {Icon ? <Icon size={18} className="ds-card-section__icon" strokeWidth={1.75} aria-hidden /> : null}
        <span>{title}</span>
      </h2>
      {action}
    </header>
    <div className="ds-card-section__body">{children}</div>
  </div>
);
