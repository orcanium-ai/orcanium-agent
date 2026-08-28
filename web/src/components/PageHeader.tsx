import React from "react";

interface PageHeaderProps {
  icon: React.ReactNode;
  title?: string;
  description: string;
  children?: React.ReactNode;
  hideDescription?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  icon,
  description,
  children,
  hideDescription,
}) => {
  return (
    <div className="flex items-center justify-between gap-4">
      <div
        className={`flex items-center gap-3 min-w-0 ${hideDescription ? "lg:flex hidden" : ""}`}
      >
        <div className="p-1.5 rounded-lg shrink-0">{icon}</div>
        <div className="min-w-0">
          <p className="text-[11px] text-neutral-300 mt-0.5 truncate">
            {description}
          </p>
        </div>
      </div>
      {children && (
        <div className="flex items-center gap-2 shrink-0">{children}</div>
      )}
    </div>
  );
};
