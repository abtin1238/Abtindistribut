from app.core.richtext import clean_html, to_text


def test_strips_scripts_and_handlers():
    h = clean_html('<script>alert(1)</script><p onclick="x()">hi<img src=x onerror=alert(1)></p>')
    assert h == '<p>hi</p>'


def test_links_only_safe_schemes():
    h = clean_html('<a href="javascript:alert(1)">bad</a><a href="//evil.com">e</a><a href="https://a.com/?x=1&y=2">ok</a>')
    assert 'javascript' not in h and 'evil.com' not in h
    assert 'href="https://a.com/?x=1&amp;y=2"' in h and 'rel="noopener noreferrer"' in h


def test_style_whitelist():
    h = clean_html('<span style="color:#ff0000;position:fixed;background:url(javascript:1)">x</span>')
    assert 'color:#ff0000' in h and 'position' not in h and 'url' not in h


def test_empty_and_text():
    assert clean_html('<p><br></p>') == '' and clean_html(None) == ''
    assert to_text('<p>a</p><p>b<br>c</p>') == 'a\nb\nc'


def test_unclosed_tags_are_closed_and_length_capped():
    assert clean_html('<p>a <b>b') == '<p>a <strong>b</strong></p>'
    assert len(clean_html('<p>' + 'x' * 50000 + '</p>', 1000)) < 1100
