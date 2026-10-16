from __future__ import annotations
import os
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.common import ESC, audit, like_pat, obj
from app.core.config import ROOT, utcnow
from app.core.security import has_all, has_perm, need, own_orders
from app.models import Category, Customer, Delivery, Invoice, Notification, Order, OrderItem, Payment, Product, Setting, Stock
from app.schemas import InvoiceTermsIn
from app.services.accounting import party_balances, vat_percent
from app.services.profit import profit_lines, summarize
from app.services.files import sniff_type  # noqa: F401
from .schemas import ThemeIn, BrandingIn, TaxIn
import glob

MAX_UPLOAD=int(os.getenv('MAX_UPLOAD_BYTES',str(10*1024*1024)))

DOC_ENTITIES={'customer','product','order','invoice','purchase','supplier','delivery','visit','employee','check','contract','payment'}

def brand_dict(s,cid):
 d={x.key:x.value for x in s.scalars(select(Setting).where(Setting.company_id==cid))}
 return {'name':d.get('brand_name',''),'tagline':d.get('brand_tagline',''),'color':d.get('brand_color','#2f7bff'),'has_logo':bool(d.get('logo_ext')),'logo_url':f"/api/brand/logo/{cid}?v={d.get('logo_v','0')}" if d.get('logo_ext') else None}

def set_kv(s,cid,k,v):
 x=s.scalar(select(Setting).where(Setting.company_id==cid,Setting.key==k))
 if x: x.value=v
 else: s.add(Setting(company_id=cid,key=k,value=v))

def logo_files(cid): return glob.glob(os.path.join(ROOT,'uploads',str(cid),'brand_logo.*'))

def theme_dict(s,cid):
 d={x.key:x.value for x in s.scalars(select(Setting).where(Setting.company_id==cid))}
 return {'color':d.get('brand_color','#2f7bff'),'radius':int(d.get('theme_radius') or 16),'font_scale':int(d.get('theme_font') or 100),'mode':d.get('theme_mode') or 'system'}

def notifications(ctx, s: Session):
 u,cid,r=ctx;return [obj(x) for x in s.scalars(select(Notification).where(Notification.company_id==cid,Notification.user_id==u.id).order_by(Notification.id.desc()).limit(100)).all()]

def notification_read(nid: int, ctx, s: Session):
 u,cid,r=ctx;q=s.get(Notification,nid)
 if not q or q.company_id!=cid or q.user_id!=u.id:raise HTTPException(404,'اعلان یافت نشد')
 q.read=True;s.commit();return obj(q)

def dashboard(ctx, s: Session):
 cid=ctx[1];r=ctx[2];today=utcnow().date();ok=lambda p:has_perm(r,p);out={}
 if ok('sales.read'):
  orders=s.scalars(select(Order).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)==today)).all();out['sales_today']=sum((o.total for o in orders),Decimal(0));out['orders_today']=len(orders)
  out['open_invoices']=s.scalar(select(func.count()).select_from(Invoice).where(Invoice.company_id==cid,Invoice.status.in_(['open','partial']))) or 0
 if ok('crm.read'): out['customers']=s.scalar(select(func.count()).select_from(Customer).where(Customer.company_id==cid,Customer.active==True))
 if ok('inventory.read'): out['stock_value']=s.scalar(select(func.sum(Stock.quantity*Product.avg_cost)).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid)) or 0;out['unvalued_products']=s.scalar(select(func.count(func.distinct(Product.id))).select_from(Stock).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid,Stock.quantity>0,Product.avg_cost<=0)) or 0
 if ok('finance.read'):
  out['receivables']=sum(party_balances(s,cid,'customer').values(),Decimal(0));out['gross_profit_month']=summarize(*profit_lines(s,cid,today.replace(day=1),today))['gross_profit'];out['payments_today']=s.scalar(select(func.sum(Payment.amount)).where(Payment.company_id==cid,func.date(Payment.created_at)==today)) or 0
 if ok('delivery.read'):
  q=select(func.count()).select_from(Delivery).where(Delivery.company_id==cid,Delivery.status.in_(['assigned','out_for_delivery']))
  if not (ok('delivery.read.all') or '*' in (r.permissions or [])): q=q.where(Delivery.driver_id==ctx[0].id)
  out['active_deliveries']=s.scalar(q) or 0
 return {k:out.get(k) for k in ('sales_today','orders_today','customers','stock_value','receivables','payments_today','active_deliveries','open_invoices','gross_profit_month','unvalued_products')}

def search(q: str, ctx, s: Session):
 u,cid,r=ctx;like=like_pat(q);out={'customers':[],'products':[],'orders':[]}
 if has_perm(r,'crm.read'): out['customers']=[obj(x) for x in s.scalars(select(Customer).where(Customer.company_id==cid,or_(Customer.name.like(like,escape=ESC),Customer.code.like(like,escape=ESC))).limit(20))]
 if has_perm(r,'catalog.read'): out['products']=[obj(x) for x in s.scalars(select(Product).where(Product.company_id==cid,or_(Product.name.like(like,escape=ESC),Product.sku.like(like,escape=ESC))).limit(20))]
 if has_perm(r,'sales.read'):
  oq=select(Order).where(Order.company_id==cid,Order.number.like(like,escape=ESC))
  if not has_all(r): oq=oq.where(own_orders(u))
  out['orders']=[obj(x) for x in s.scalars(oq.limit(20))]
 return out

def dash_trend(days: int, ctx, s: Session):
 cid=ctx[1];start=date.today()-timedelta(days=days-1)
 rows=s.execute(select(func.date(Order.created_at),func.sum(Order.total)).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)>=start).group_by(func.date(Order.created_at))).all()
 m={str(d):v for d,v in rows}
 return [{'day':str(start+timedelta(i)),'total':m.get(str(start+timedelta(i)),0)} for i in range(days)]

def dash_cat(days: int, ctx, s: Session):
 cid=ctx[1];start=date.today()-timedelta(days=days-1)
 rows=s.execute(select(func.coalesce(Category.name,'سایر'),func.sum(OrderItem.quantity*OrderItem.unit_price-OrderItem.discount)).select_from(OrderItem).join(Order,Order.id==OrderItem.order_id).join(Product,Product.id==OrderItem.product_id).outerjoin(Category,Category.id==Product.category_id).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)>=start).group_by(Category.name)).all()
 return [{'name':n,'total':t} for n,t in rows]

def theme_get(ctx, s: Session):
 return theme_dict(s, ctx[1])

def theme_put(x: ThemeIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');set_kv(s,cid,'brand_color',x.color);set_kv(s,cid,'theme_radius',str(x.radius));set_kv(s,cid,'theme_font',str(x.font_scale));set_kv(s,cid,'theme_mode',x.mode);audit(s,cid,u.id,'update','theme',None,x.model_dump());s.commit();return theme_dict(s,cid)

def brand_get(ctx, s: Session):
 return brand_dict(s, ctx[1])

def brand_put(x: BrandingIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');set_kv(s,cid,'brand_name',x.name.strip());set_kv(s,cid,'brand_tagline',x.tagline.strip());set_kv(s,cid,'brand_color',x.color);audit(s,cid,u.id,'update','brand',None,x.model_dump());s.commit();return brand_dict(s,cid)

async def logo_upload(file: UploadFile, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');data=await file.read()
 if len(data)>1048576: raise HTTPException(400,'حجم لوگو بیشتر از ۱ مگابایت است')
 ext='png' if data[:8]==b'\x89PNG\r\n\x1a\n' else 'jpg' if data[:3]==b'\xff\xd8\xff' else 'webp' if data[:4]==b'RIFF' and data[8:12]==b'WEBP' else None
 if not ext: raise HTTPException(400,'فقط PNG، JPG یا WebP مجاز است')
 folder=os.path.join(ROOT,'uploads',str(cid));os.makedirs(folder,exist_ok=True)
 for f in logo_files(cid): os.remove(f)
 open(os.path.join(folder,'brand_logo.'+ext),'wb').write(data);set_kv(s,cid,'logo_ext',ext);set_kv(s,cid,'logo_v',str(int(utcnow().timestamp())));audit(s,cid,u.id,'upload','brand_logo');s.commit();return brand_dict(s,cid)

def logo_delete(ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write')
 for f in logo_files(cid): os.remove(f)
 set_kv(s,cid,'logo_ext','');audit(s,cid,u.id,'delete','brand_logo');s.commit();return brand_dict(s,cid)

def logo_get(cid: int, s: Session):
 ext=s.scalar(select(Setting.value).where(Setting.company_id==cid,Setting.key=='logo_ext'));fs=logo_files(cid)
 if not ext or not fs: raise HTTPException(404,'لوگو یافت نشد')
 return FileResponse(fs[0],media_type={'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[ext],headers={'Cache-Control':'public, max-age=31536000'})

def tax_get(ctx, s: Session):
 return {'vat_percent': vat_percent(s, ctx[1])}

def tax_put(x: TaxIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');set_kv(s,cid,'vat_percent',str(x.vat_percent));audit(s,cid,u.id,'update','tax',None,x.model_dump());s.commit();return {'vat_percent':x.vat_percent}

def invoice_terms_get(ctx, s: Session):
 return {'terms': s.scalar(select(Setting.value).where(Setting.company_id == ctx[1], Setting.key == 'invoice_terms')) or ''}

def invoice_terms_put(x: InvoiceTermsIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');set_kv(s,cid,'invoice_terms',x.terms);audit(s,cid,u.id,'update','invoice_terms');s.commit();return {'terms':x.terms}
