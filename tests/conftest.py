import os
# Rate limit در سوئیت تست خاموش است (همه‌ی تست‌ها از یک IP و پشت‌سرهم لاگین می‌کنند)؛ تست‌های مخصوصش مقدار را موقتاً عوض می‌کنند.
os.environ.setdefault('RATE_LIMIT_PER_MIN','0')
os.environ.setdefault('RATE_LIMIT_LOGIN_PER_MIN','0')
os.environ.setdefault('WEBHOOK_ALLOW_PRIVATE','1')

try:  # پروفایل hypothesis برای CI: قطعی (derandomize) و بدون deadline تا تست‌ها flaky نشوند
    from hypothesis import settings as _hs
    _hs.register_profile('ci', derandomize=True, deadline=None, max_examples=100)
    _hs.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'ci'))
except ImportError:
    pass
