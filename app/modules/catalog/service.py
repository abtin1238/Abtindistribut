from __future__ import annotations
from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D, audit, list_json, list_page, obj, same_company
from app.core.security import need
from app.models import Campaign, Customer, Brand, Category, PriceRule, Product, Stock, UnitConversion
from app.services.accounting import price_quote
from .schemas import ProductIn, ProductPatch, BrandIn, CategoryIn, PriceRuleIn, UnitIn, CampaignIn

def _check_refs(s,cid,brand_id,category_id):
 if brand_id is not None and not s.scalar(select(Brand.id).where(Brand.id==brand_id,Brand.company_id==cid)): raise HTTPException(404,'برند یافت نشد')
 if category_id is not None and not s.scalar(select(Category.id).where(Category.id==category_id,Category.company_id==cid)): raise HTTPException(404,'دسته یافت نشد')

def _barcode_free(s,cid,code,product_id=None,unit_id=None):
 """بارکد در سطح شرکت یکتاست (بین بارکد کالا و بارکد واحدهای فرعی)"""
 if not code: return
 q=select(Product.id).where(Product.company_id==cid,Product.barcode==code)
 if product_id is not None: q=q.where(Product.id!=product_id)
 if s.scalar(q): raise HTTPException(409,'این بارکد برای کالای دیگری ثبت شده است')
 q=select(UnitConversion.id).where(UnitConversion.company_id==cid,UnitConversion.barcode==code)
 if unit_id is not None: q=q.where(UnitConversion.id!=unit_id)
 if s.scalar(q): raise HTTPException(409,'این بارکد برای واحد فرعی کالای دیگری ثبت شده است')

def patch_product(pid: int, x: ProductPatch, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); p=same_company(s,Product,pid,cid); d=x.model_dump(exclude_unset=True)
 _check_refs(s,cid,d.get('brand_id'),d.get('category_id'))
 if 'barcode' in d:
  d['barcode']=(d['barcode'] or '').strip() or None;_barcode_free(s,cid,d['barcode'],p.id)
 if 'name' in d and not (d['name'] or '').strip(): raise HTTPException(400,'نام کالا الزامی است')
 if (d.get('base_price') or 0)<0 or (d.get('min_stock') or 0)<0: raise HTTPException(400,'مقدار منفی مجاز نیست')
 for k,v in d.items(): setattr(p,k,v)
 audit(s,cid,u.id,'update','product',p.id,d);s.commit();s.refresh(p);return obj(p)

def brands(ctx, s: Session):
 return [obj(b) for b in s.scalars(select(Brand).where(Brand.company_id == ctx[1]).order_by(Brand.name)).all()]

def add_brand(x: BrandIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); n=x.name.strip()
 if not n: raise HTTPException(400,'نام برند الزامی است')
 if s.scalar(select(Brand.id).where(Brand.company_id==cid,Brand.name==n)): raise HTTPException(409,'این برند قبلاً ثبت شده است')
 b=Brand(company_id=cid,name=n);s.add(b);s.flush();audit(s,cid,u.id,'create','brand',b.id,{'name':n});s.commit();return obj(b)

def del_brand(bid: int, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); b=same_company(s,Brand,bid,cid)
 if s.scalar(select(Product.id).where(Product.brand_id==b.id)): raise HTTPException(409,'این برند به کالا متصل است')
 s.delete(b);audit(s,cid,u.id,'delete','brand',bid,{});s.commit();return {'ok':True}

def categories(ctx, s: Session):
 return [obj(c) for c in s.scalars(select(Category).where(Category.company_id == ctx[1]).order_by(Category.name)).all()]

def add_category(x: CategoryIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); n=x.name.strip()
 if not n: raise HTTPException(400,'نام دسته الزامی است')
 if x.parent_id is not None: same_company(s,Category,x.parent_id,cid)
 if s.scalar(select(Category.id).where(Category.company_id==cid,Category.name==n,Category.parent_id==x.parent_id)): raise HTTPException(409,'این دسته قبلاً ثبت شده است')
 c=Category(company_id=cid,name=n,parent_id=x.parent_id);s.add(c);s.flush();audit(s,cid,u.id,'create','category',c.id,{'name':n});s.commit();return obj(c)

def del_category(cid_: int, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); c=same_company(s,Category,cid_,cid)
 if s.scalar(select(Product.id).where(Product.category_id==c.id)) or s.scalar(select(Category.id).where(Category.parent_id==c.id)): raise HTTPException(409,'این دسته در حال استفاده است')
 s.delete(c);audit(s,cid,u.id,'delete','category',cid_,{});s.commit();return {'ok':True}

def products(response: Response, limit: int, offset: int, ctx, s: Session):
 return [obj(x) for x in list_page(s, Product, ctx[1], response, limit, offset)]

def add_product(x: ProductIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write');_check_refs(s,cid,x.brand_id,x.category_id)
 x.barcode=(x.barcode or '').strip() or None;_barcode_free(s,cid,x.barcode)
 if x.base_price<0 or x.min_stock<0: raise HTTPException(400,'مقدار منفی مجاز نیست')
 q=Product(company_id=cid,**x.model_dump());s.add(q);audit(s,cid,u.id,'create','product');s.commit();s.refresh(q);return obj(q)

def price_rules(ctx, s: Session):
 return [obj(x) for x in list_json(s, PriceRule, ctx[1])]

def add_price_rule(x: PriceRuleIn, ctx, s: Session):
 u,cid,r=ctx;p=s.get(Product,x.product_id)
 if not p or p.company_id!=cid: raise HTTPException(404,'کالا یافت نشد')
 if x.price is None and not (0<x.discount_percent<=100): raise HTTPException(400,'قیمت ثابت یا درصد تخفیف (۰ تا ۱۰۰) لازم است')
 if x.price is not None and x.price<0: raise HTTPException(400,'قیمت منفی مجاز نیست')
 if x.starts_at and x.ends_at and x.ends_at<x.starts_at: raise HTTPException(400,'پایان قانون قبل از شروع آن است')
 q=PriceRule(company_id=cid,**x.model_dump());s.add(q);audit(s,cid,u.id,'create','price_rule');s.commit();s.refresh(q);return obj(q)

def toggle_price_rule(rid: int, active: bool, ctx, s: Session):
 u,cid,r=ctx;q=same_company(s,PriceRule,rid,cid);q.active=active;audit(s,cid,u.id,'update','price_rule',q.id,{'active':active});s.commit();return obj(q)

def del_price_rule(rid: int, ctx, s: Session):
 u,cid,r=ctx;q=same_company(s,PriceRule,rid,cid);s.delete(q);audit(s,cid,u.id,'delete','price_rule',rid,{});s.commit();return {'ok':True}

def quote(product_id: int, quantity: float, customer_id: int | None, ctx, s: Session):
 """قیمت واحد و جمع برای یک کالا/مشتری/تعداد، همراه با دلیل قانون اعمال‌شده (برای شفافیت قیمت)"""
 cid=ctx[1];p=same_company(s,Product,product_id,cid);grp=''
 if quantity<=0: raise HTTPException(400,'تعداد باید مثبت باشد')
 if customer_id is not None: grp=same_company(s,Customer,customer_id,cid).customer_group or ''
 q=price_quote(s,cid,p.id,grp,quantity)
 from decimal import Decimal
 return {'product_id':p.id,'quantity':quantity,'customer_group':grp,'unit_price':str(q['price']),'base_price':str(q['base_price']),'total':str((Decimal(str(quantity))*q['price']).quantize(Decimal('0.01'))),'rule_id':q['rule_id'],'reason':q['reason']}

def units(pid: int, ctx, s: Session):
 p=same_company(s,Product,pid,ctx[1])
 return {'base_unit':p.unit,'units':[obj(x) for x in s.scalars(select(UnitConversion).where(UnitConversion.product_id==p.id).order_by(UnitConversion.factor))]}

def add_unit(pid: int, x: UnitIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); p=same_company(s,Product,pid,cid); n=x.unit.strip()
 if not n: raise HTTPException(400,'نام واحد الزامی است')
 if n==p.unit: raise HTTPException(400,'واحد فرعی نباید با واحد پایه یکی باشد')
 if s.scalar(select(UnitConversion.id).where(UnitConversion.product_id==p.id,UnitConversion.unit==n)): raise HTTPException(409,'این واحد قبلاً تعریف شده است')
 code=(x.barcode or '').strip() or None;_barcode_free(s,cid,code)
 uc=UnitConversion(company_id=cid,product_id=p.id,unit=n,factor=x.factor,barcode=code);s.add(uc);s.flush();audit(s,cid,u.id,'create','unit_conversion',uc.id,{'product_id':p.id,'unit':n,'factor':str(x.factor)});s.commit();return obj(uc)

def del_unit(uid: int, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'catalog.write'); uc=same_company(s,UnitConversion,uid,cid)
 s.delete(uc);audit(s,cid,u.id,'delete','unit_conversion',uid,{});s.commit();return {'ok':True}

def by_barcode(code: str, ctx, s: Session):
 """پیدا کردن کالا با بارکد (کالا یا واحد فرعی) برای اسکن در اپ بازاریاب/انبار"""
 cid=ctx[1];code=code.strip()
 p=s.scalar(select(Product).where(Product.company_id==cid,Product.barcode==code));unit=p.unit if p else None;factor=1
 if not p:
  uc=s.scalar(select(UnitConversion).where(UnitConversion.company_id==cid,UnitConversion.barcode==code))
  if not uc: raise HTTPException(404,'کالایی با این بارکد یافت نشد')
  p=s.get(Product,uc.product_id);unit=uc.unit;factor=uc.factor
 return {'product':obj(p),'unit':unit,'factor':factor}

def compare(ids: str, customer_id: int | None, ctx, s: Session):
 """مقایسهٔ ۲ تا ۶ کالا: مشخصات، قیمت (ویژهٔ مشتری در صورت ارسال) و موجودی قابل فروش"""
 cid=ctx[1]
 try: pids=list(dict.fromkeys(int(x) for x in ids.split(',') if x.strip()))
 except ValueError: raise HTTPException(400,'شناسه‌ها نامعتبر است')
 if not 2<=len(pids)<=6: raise HTTPException(400,'برای مقایسه ۲ تا ۶ کالا لازم است')
 grp=''
 if customer_id is not None: grp=same_company(s,Customer,customer_id,cid).customer_group
 rows=[];keys=[]
 for pid in pids:
  p=same_company(s,Product,pid,cid);avail=sum((D(a)-D(b) for a,b in s.execute(select(Stock.quantity,Stock.reserved).where(Stock.product_id==p.id))),D(0))
  specs=p.specs or {}
  for k in specs:
   if k not in keys: keys.append(k)
  rows.append({'id':p.id,'sku':p.sku,'name':p.name,'unit':p.unit,'barcode':p.barcode,'brand_id':p.brand_id,'category_id':p.category_id,'base_price':p.base_price,'price':price_quote(s,cid,p.id,grp,1)['price'],'available':avail,'specs':specs})
 return {'spec_keys':keys,'products':rows}

def campaigns(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(Campaign).where(Campaign.company_id==ctx[1]).order_by(Campaign.id.desc()))]

def add_campaign(x: CampaignIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'pricing.write')
 if x.product_id is not None: same_company(s,Product,x.product_id,cid)
 if x.starts_at and x.ends_at and x.ends_at<x.starts_at: raise HTTPException(400,'پایان کمپین قبل از شروع آن است')
 code=(x.code or '').strip() or None
 if code and s.scalar(select(Campaign.id).where(Campaign.company_id==cid,Campaign.code==code)): raise HTTPException(409,'کد کمپین تکراری است')
 c=Campaign(company_id=cid,**{**x.model_dump(),'code':code,'name':x.name.strip()});s.add(c);s.flush();audit(s,cid,u.id,'create','campaign',c.id,x.model_dump(mode='json'));s.commit();return obj(c)

def toggle_campaign(cid_: int, active: bool, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'pricing.write'); c=same_company(s,Campaign,cid_,cid);c.active=active;audit(s,cid,u.id,'update','campaign',c.id,{'active':active});s.commit();return obj(c)

def del_campaign(cid_: int, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'pricing.write'); c=same_company(s,Campaign,cid_,cid);s.delete(c);audit(s,cid,u.id,'delete','campaign',cid_,{});s.commit();return {'ok':True}
