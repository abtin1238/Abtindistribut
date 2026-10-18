from __future__ import annotations
from datetime import date
MONTHS=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند']
def to_jalali(d:date)->tuple[int,int,int]:
    gy,gm,gd=d.year,d.month,d.day;g=[0,31,59,90,120,151,181,212,243,273,304,334]
    gy2=gy+1 if gm>2 else gy;days=355666+365*gy+(gy2+3)//4-(gy2+99)//100+(gy2+399)//400+gd+g[gm-1]
    jy=-1595+33*(days//12053);days%=12053;jy+=4*(days//1461);days%=1461
    if days>365:jy+=(days-1)//365;days=(days-1)%365
    jm,jd=(1+days//31,1+days%31) if days<186 else (7+(days-186)//30,1+(days-186)%30)
    return jy,jm,jd
_JDM=[31,31,31,31,31,31,30,30,30,30,30,29]
_GDM=[31,28,31,30,31,30,31,31,30,31,30,31]
def from_jalali(jy:int,jm:int,jd:int)->date:
    """تبدیل تاریخ شمسی به میلادی (الگوریتم استاندارد 33ساله)؛ در ورودی نامعتبر ValueError می‌دهد."""
    if not (1<=jm<=12) or jd<1 or jd>(_JDM[jm-1] if jm<12 else 30): raise ValueError('تاریخ شمسی نامعتبر است')
    y=jy-979;n=365*y+(y//33)*8+((y%33+3)//4)+sum(_JDM[:jm-1])+(jd-1);g=n+79
    gy=1600+400*(g//146097);g%=146097;leap=True
    if g>=36525:
        g-=1;gy+=100*(g//36524);g%=36524
        if g>=365:g+=1
        else:leap=False
    gy+=4*(g//1461);g%=1461
    if g>=366:leap=False;g-=1;gy+=g//365;g%=365
    i=0
    while g>=_GDM[i]+(1 if i==1 and leap else 0):g-=_GDM[i]+(1 if i==1 and leap else 0);i+=1
    r=date(gy,i+1,g+1)
    if to_jalali(r)!=(jy,jm,jd): raise ValueError('تاریخ شمسی نامعتبر است')
    return r
_DIG=str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')
def parse_jalali(v:str)->date:
    """'1405/07/19' یا '۱۴۰۵-۰۷-۱۹' → date میلادی"""
    p=[x for x in str(v).translate(_DIG).replace('-','/').replace('.','/').strip().split('/') if x!='']
    if len(p)!=3 or not all(x.isdigit() for x in p): raise ValueError('تاریخ شمسی باید به شکل 1405/07/19 باشد')
    return from_jalali(int(p[0]),int(p[1]),int(p[2]))
def fmt_jalali(d)->str:
    y,m,dd=to_jalali(d.date() if hasattr(d,'date') else d);return f'{y:04d}/{m:02d}/{dd:02d}'
