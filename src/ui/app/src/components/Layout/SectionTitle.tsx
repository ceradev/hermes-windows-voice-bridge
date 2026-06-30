import type { LucideIcon } from 'lucide-react';

type SectionTitleProps = {
  icon?: LucideIcon;
  children: React.ReactNode;
  flush?: boolean;
};

export const SectionTitle = ({ icon: Icon, children, flush = false }: SectionTitleProps) => (
  <div className={`ds-section-title${flush ? ' ds-section-title--flush' : ''}`}>
    {Icon ? <Icon className="ds-section-title__icon" size={18} strokeWidth={1.75} aria-hidden /> : null}
    <h2 className="ds-section-title__text">{children}</h2>
  </div>
);
