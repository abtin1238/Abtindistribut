from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.schemas import BrandIn, CategoryIn, PriceRuleIn, ProductIn, ProductPatch, UnitIn, CampaignIn
from .service import patch_product as _s_patch_product, brands as _s_brands, add_brand as _s_add_brand, del_brand as _s_del_brand, categories as _s_categories, add_category as _s_add_category, del_category as _s_del_category, products as _s_products, add_product as _s_add_product, price_rules as _s_price_rules, add_price_rule as _s_add_price_rule, toggle_price_rule as _s_toggle_price_rule, del_price_rule as _s_del_price_rule, quote as _s_quote

router=APIRouter()

@router.get('/api/products/compare')
def compare_products(ids: str=Query(..., max_length=100), customer_id: int | None=Query(default=None), ctx=Depends(current), s: Session=Depends(db)):
 from .service import compare as _c
 return _c(ids=ids, customer_id=customer_id, ctx=ctx, s=s)

@router.get('/api/products/by-barcode/{code}')
def product_by_barcode(code: str, ctx=Depends(current), s: Session=Depends(db)):
 from .service import by_barcode as _b
 return _b(code=code, ctx=ctx, s=s)

@router.get('/api/products/{pid}/units')
def product_units(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 from .service import units as _u
 return _u(pid=pid, ctx=ctx, s=s)

@router.post('/api/products/{pid}/units')
def add_product_unit(pid: int, x: UnitIn, ctx=Depends(current), s: Session=Depends(db)):
 from .service import add_unit as _a
 return _a(pid=pid, x=x, ctx=ctx, s=s)

@router.delete('/api/product-units/{uid}')
def del_product_unit(uid: int, ctx=Depends(current), s: Session=Depends(db)):
 from .service import del_unit as _d
 return _d(uid=uid, ctx=ctx, s=s)

@router.patch('/api/products/{pid}')
def patch_product(pid: int, x: ProductPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_patch_product(pid=pid, x=x, ctx=ctx, s=s)

@router.get('/api/brands')
def brands(ctx=Depends(current), s: Session=Depends(db)):
 return _s_brands(ctx=ctx, s=s)

@router.post('/api/brands')
def add_brand(x: BrandIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_brand(x=x, ctx=ctx, s=s)

@router.delete('/api/brands/{bid}')
def del_brand(bid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_del_brand(bid=bid, ctx=ctx, s=s)

@router.get('/api/categories')
def categories(ctx=Depends(current), s: Session=Depends(db)):
 return _s_categories(ctx=ctx, s=s)

@router.post('/api/categories')
def add_category(x: CategoryIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_category(x=x, ctx=ctx, s=s)

@router.delete('/api/categories/{cid_}')
def del_category(cid_: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_del_category(cid_=cid_, ctx=ctx, s=s)

@router.get('/api/products')
def products(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_products(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.post('/api/products')
def add_product(x: ProductIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_product(x=x, ctx=ctx, s=s)

@router.get('/api/price-rules')
def price_rules(ctx=Depends(current), s: Session=Depends(db)):
 return _s_price_rules(ctx=ctx, s=s)

@router.post('/api/price-rules')
def add_price_rule(x: PriceRuleIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_price_rule(x=x, ctx=ctx, s=s)

@router.patch('/api/price-rules/{rid}')
def toggle_price_rule(rid: int, active: bool, ctx=Depends(current), s: Session=Depends(db)):
 return _s_toggle_price_rule(rid=rid, active=active, ctx=ctx, s=s)

@router.delete('/api/price-rules/{rid}')
def del_price_rule(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_del_price_rule(rid=rid, ctx=ctx, s=s)

@router.get('/api/pricing/quote')
def quote(product_id: int, quantity: float=1, customer_id: int | None=None, ctx=Depends(current), s: Session=Depends(db)):
 'قیمت واحد و جمع برای یک کالا/مشتری/تعداد، همراه با دلیل قانون اعمال\u200cشده (برای شفافیت قیمت)'
 return _s_quote(product_id=product_id, quantity=quantity, customer_id=customer_id, ctx=ctx, s=s)

@router.get('/api/campaigns')
def campaigns(ctx=Depends(current), s: Session=Depends(db)):
 from .service import campaigns as _f
 return _f(ctx=ctx, s=s)

@router.post('/api/campaigns')
def add_campaign(x: CampaignIn, ctx=Depends(current), s: Session=Depends(db)):
 from .service import add_campaign as _f
 return _f(x=x, ctx=ctx, s=s)

@router.patch('/api/campaigns/{cid_}')
def toggle_campaign(cid_: int, active: bool=Query(...), ctx=Depends(current), s: Session=Depends(db)):
 from .service import toggle_campaign as _f
 return _f(cid_=cid_, active=active, ctx=ctx, s=s)

@router.delete('/api/campaigns/{cid_}')
def del_campaign(cid_: int, ctx=Depends(current), s: Session=Depends(db)):
 from .service import del_campaign as _f
 return _f(cid_=cid_, ctx=ctx, s=s)
