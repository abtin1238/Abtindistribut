# بارگذاری تنبل: import این پکیج router را بالا نمی‌آورد (جلوگیری از import حلقوی با models/schemas)
# نام‌های router.py و service.py هنوز مثل قبل از خود پکیج در دسترس‌اند: `from app.modules.finance import payment`
from importlib import import_module as _im

_SUBS=('router', 'service')


def __getattr__(name):
    if name.startswith('__'): raise AttributeError(name)
    for s in _SUBS:
        mod=_im(f'{__name__}.{s}')
        if hasattr(mod,name): return getattr(mod,name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
