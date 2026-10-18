// Expose the reusable module API for legacy pages without changing existing script ordering.
import * as DynamicStyles from "/web/js/styles.js";
window.DynamicStyles = DynamicStyles;
const meta = document.querySelector('meta[name="theme-color"]');
if (meta) meta.content = getComputedStyle(document.documentElement).getPropertyValue('--bg0').trim() || getComputedStyle(document.documentElement).getPropertyValue('--bg').trim() || getComputedStyle(document.documentElement).getPropertyValue('--bl').trim();
