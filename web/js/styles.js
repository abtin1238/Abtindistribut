/** Reusable dynamic style API. Import from any ES module: import { setTokens, setTheme, cssVar } from "/web/js/styles.js"; */
const root = document.documentElement;
const getRuntime = () => globalThis.Tokens || globalThis.DynamicStylesRuntime || null;
export function setTokens(tokens = {}) { const runtime = getRuntime(); if (runtime?.set) runtime.set(tokens); else for (const [key,value] of Object.entries(tokens)) if (/^--[a-z0-9-]+$/i.test(key)) root.style.setProperty(key, String(value)); return tokens; }
export function cssVar(name, fallback = "") { const value = getComputedStyle(root).getPropertyValue(name).trim(); return value || fallback; }
export function setTheme(theme = {}) { const runtime = getRuntime(); if (runtime?.apply) runtime.apply(theme); else setTokens(Object.fromEntries(Object.entries(theme).filter(([key]) => key.startsWith("--")))); return theme; }
export function toggleTheme() { const runtime = getRuntime(); if (runtime?.toggle) return runtime.toggle(); root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark"; return root.dataset.theme; }
export function currentTheme() { return root.dataset.theme || "system"; }
export default { setTokens, setTheme, cssVar, toggleTheme, currentTheme };
