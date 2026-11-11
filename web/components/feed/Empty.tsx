import type { ReactNode } from "react";
export default function Empty({ title, children, action, icon }: { title: string; children?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      {icon && <div className="mb-1 text-faint">{icon}</div>}
      <div className="text-[15px] font-medium text-bone">{title}</div>
      {children && <p className="max-w-[44ch] text-[15px] text-muted">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
