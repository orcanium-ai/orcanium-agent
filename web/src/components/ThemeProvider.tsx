import React, { useEffect } from "react";
import { useSettingsStore } from "../stores/settingsStore";

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const theme = useSettingsStore((s) => s.theme);

  useEffect(() => {
    const body = document.body;
    body.classList.remove(
      "theme-slate",
      "theme-violet",
      "theme-emerald",
      "theme-amber",
    );
    body.classList.add(`theme-${theme}`);
  }, [theme]);

  return <>{children}</>;
};
