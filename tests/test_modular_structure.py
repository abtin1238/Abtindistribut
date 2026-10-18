"""ساختار ماژولار: هر ماژول models/schemas/service/router خودش را دارد و facadeهای قدیمی همه‌چیز را برمی‌گردانند."""
import importlib,os,pkgutil
import app.modules as mods
from app.core.database import Base
import app.models,app.schemas  # noqa: F401


def _packages():
    return [m.name for m in pkgutil.iter_modules(mods.__path__) if m.ispkg]


def test_every_module_has_router_and_lazy_init():
    for name in _packages():
        r=importlib.import_module(f'app.modules.{name}.router')
        assert hasattr(r,'router'),name


def test_models_facade_covers_metadata():
    tables={t.name for t in Base.metadata.sorted_tables}
    from_modules=set()
    for name in _packages()+['core']:
        base='app.core' if name=='core' else f'app.modules.{name}'
        try: m=importlib.import_module(base+'.models')
        except ModuleNotFoundError: continue
        for v in vars(m).values():
            t=getattr(v,'__tablename__',None)
            if t and getattr(v,'__module__',None)==m.__name__: from_modules.add(t)
    assert from_modules==tables


def test_legacy_package_attrs_still_resolve():
    from app.modules.finance import add_check,payment  # noqa: F401
    from app.modules.platform import MAX_UPLOAD  # noqa: F401
    from app.modules.automation import run_reminders  # noqa: F401


def test_no_service_imports_router():
    root=os.path.dirname(mods.__file__)
    for name in _packages():
        p=os.path.join(root,name,'service.py')
        if os.path.exists(p): assert '.router' not in open(p,encoding='utf-8').read(),name
