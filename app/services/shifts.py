"""محاسبهٔ تأخیر/تعجیل/اضافه‌کاری حضور نسبت به شیفت (تابع خالص؛ زمان‌های ذخیره‌شده UTC بدون tz هستند)."""
from __future__ import annotations
import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

def local_tz() -> ZoneInfo: return ZoneInfo(os.environ.get('LOCAL_TZ', 'Asia/Tehran'))

def to_local(dt: datetime, tz: ZoneInfo | None = None) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(tz or local_tz())

def _mins(a: datetime, b: datetime) -> int: return int((b - a).total_seconds() // 60)

def shift_metrics(day: date, check_in: datetime, check_out: datetime | None, start: time, end: time, grace: int = 0, tz: ZoneInfo | None = None) -> dict:
    """late: دقایق ورود پس از (شروع+مهلت) — از خود شروع شیفت شمرده می‌شود؛ early_leave: خروج پیش از پایان؛ overtime: خروج پس از پایان؛
    شیفت شب‌کار (end<=start) پایان را به روز بعد می‌برد. بدون خروج: فقط تأخیر محاسبه می‌شود."""
    from datetime import timedelta
    tz = tz or local_tz()
    s = datetime.combine(day, start, tzinfo=tz); e = datetime.combine(day, end, tzinfo=tz)
    if e <= s: e += timedelta(days=1)
    cin = to_local(check_in, tz); late = _mins(s, cin) if cin > s + timedelta(minutes=grace) else 0
    early = overtime = worked = 0
    if check_out:
        cout = to_local(check_out, tz); worked = max(0, _mins(cin, cout))
        early = max(0, _mins(cout, e)); overtime = max(0, _mins(e, cout))
    return {'late': late, 'early_leave': early, 'overtime': overtime, 'worked': worked}
