"""پاک‌سازی HTML ادیتور متن غنی (whitelist). فقط stdlib؛ هر متنی که از ادیتور می‌آید قبل از ذخیره از اینجا رد می‌شود.

قواعد: فقط تگ‌های فهرست‌شده؛ فقط صفت‌های مجاز؛ لینک فقط http/https/mailto/tel؛
style فقط color / background-color / text-align با مقدار امن؛ محتوای script/style حذف می‌شود.
"""
from __future__ import annotations
import re
from html import escape
from html.parser import HTMLParser

ALLOWED = {'p', 'br', 'strong', 'em', 'u', 's', 'h2', 'h3', 'ul', 'ol', 'li', 'blockquote', 'hr', 'a', 'span',
           'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div'}
ALIAS = {'b': 'strong', 'i': 'em', 'strike': 's', 'del': 's', 'h1': 'h2', 'h4': 'h3', 'h5': 'h3', 'h6': 'h3'}
VOID = {'br', 'hr'}
DROP_CONTENT = {'script', 'style', 'iframe', 'object', 'embed', 'noscript', 'template', 'svg', 'math', 'head', 'title'}
BLOCK = {'p', 'div', 'h2', 'h3', 'li', 'blockquote', 'tr', 'ul', 'ol', 'table'}
HEX = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
RGB = re.compile(r'^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(?:,\s*(?:0|1|0?\.\d+)\s*)?\)$')
ALIGN = {'right', 'left', 'center', 'justify'}
SAFE_URL = re.compile(r'^(?:https?://|mailto:|tel:|/(?![/\\]))', re.I)
MAX_DEPTH = 40


def _color(v: str) -> bool:
    v = v.strip()
    return bool(HEX.match(v) or RGB.match(v))


def _style(raw: str) -> str:
    out = []
    for part in (raw or '').split(';'):
        k, _, v = part.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k in ('color', 'background-color') and _color(v):
            out.append(f'{k}:{v}')
        elif k == 'text-align' and v.lower() in ALIGN:
            out.append(f'{k}:{v.lower()}')
    return ';'.join(out)


class _Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = ALIAS.get(tag.lower(), tag.lower())
        if tag in DROP_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED:
            return
        if tag in VOID:
            self.out.append(f'<{tag}>')
            return
        if len(self.stack) >= MAX_DEPTH:
            return
        a = {k.lower(): (v or '') for k, v in attrs}
        parts = ''
        if tag == 'a':
            href = a.get('href', '').strip()
            if not SAFE_URL.match(href):
                self.stack.append('')  # تگ حذف می‌شود ولی محتوا می‌ماند
                return
            parts += f' href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer"'
        else:
            st = _style(a.get('style', ''))
            if st:
                parts += f' style="{st}"'
            if a.get('dir', '').lower() in ('rtl', 'ltr') and tag in ('p', 'div', 'h2', 'h3', 'li', 'blockquote', 'ul', 'ol', 'td', 'th'):
                parts += f' dir="{a["dir"].lower()}"'
            if tag in ('td', 'th'):
                for k in ('colspan', 'rowspan'):
                    if a.get(k, '').isdigit() and 1 <= int(a[k]) <= 20:
                        parts += f' {k}="{int(a[k])}"'
        self.stack.append(tag)
        self.out.append(f'<{tag}{parts}>')

    def handle_startendtag(self, tag, attrs):
        t = ALIAS.get(tag.lower(), tag.lower())
        if t in VOID and not self.skip:
            self.out.append(f'<{t}>')

    def handle_endtag(self, tag):
        tag = ALIAS.get(tag.lower(), tag.lower())
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID or tag not in ALLOWED:
            return
        if tag in self.stack:
            while self.stack:
                t = self.stack.pop()
                if t:
                    self.out.append(f'</{t}>')
                if t == tag:
                    break
        elif tag == 'a' and '' in self.stack:
            # لینک نامعتبر که تگ ندارد: فقط از stack خارج شود
            i = len(self.stack) - 1 - self.stack[::-1].index('')
            del self.stack[i]

    def handle_data(self, data):
        if not self.skip and data:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            t = self.stack.pop()
            if t:
                self.out.append(f'</{t}>')
        return ''.join(self.out)


def clean_html(html: str | None, max_len: int = 30000) -> str:
    """HTML ورودی را پاک می‌کند؛ خروجی خالی یعنی متن بدون محتوای واقعی بود."""
    if not html:
        return ''
    if len(html) > max_len * 4:
        html = html[: max_len * 4]
    p = _Clean()
    try:
        p.feed(str(html))
        p.close()
    except Exception:
        return escape(to_text(html), quote=False)[:max_len]
    out = p.result().strip()
    if not to_text(out).strip() and '<hr>' not in out and '<table' not in out:
        return ''
    return out if len(out) <= max_len else _trim(out, max_len)


def _trim(out: str, max_len: int) -> str:
    """برش امن: بعد از برش دوباره از پاک‌ساز رد می‌شود تا تگ باز نماند."""
    cut = out[:max_len - min(300, max_len >> 2)]
    cut = cut[: cut.rfind('<')] if cut.rfind('<') > cut.rfind('>') else cut
    p = _Clean()
    p.feed(cut)
    p.close()
    return p.result()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skip += 1
        elif tag in ('br', 'hr') or tag in BLOCK:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.parts.append('\n')
        elif tag in ('td', 'th'):
            self.parts.append(' | ')

    def handle_data(self, d):
        if not self.skip:
            self.parts.append(d)


def to_text(html: str | None) -> str:
    """متن ساده‌ی HTML (برای جست‌وجو، اعلان و خروجی بدون قالب)."""
    if not html:
        return ''
    p = _Text()
    try:
        p.feed(str(html))
        p.close()
    except Exception:
        return re.sub(r'<[^>]*>', ' ', str(html))
    t = ''.join(p.parts)
    t = re.sub(r'[ \t\u00a0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t).strip()
