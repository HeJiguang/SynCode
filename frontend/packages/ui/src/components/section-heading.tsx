import * as React from "react";

type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
};

export function SectionHeading({ description, eyebrow, title }: SectionHeadingProps) {
  return (
    <div className="space-y-3">
      {eyebrow ? <p className="kicker">{eyebrow}</p> : null}
      <h2 className="section-title">{title}</h2>
      {description ? <p className="max-w-3xl text-sm leading-7 text-[var(--text-secondary)]">{description}</p> : null}
    </div>
  );
}
