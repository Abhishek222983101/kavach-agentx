"use client";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

/** Light/dark switch (ETHGlobal pattern). Dark is the default. */
export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <button type="button" aria-label="Switch between light and dark theme"
      onClick={() => setTheme(resolvedTheme === "light" ? "dark" : "light")}
      className="grid h-9 w-9 place-items-center rounded-lg text-muted transition-colors hover:bg-panel2 hover:text-bone">
      <Sun size={17} className="hidden [.light_&]:block" /><Moon size={17} className="[.light_&]:hidden" />
    </button>
  );
}
