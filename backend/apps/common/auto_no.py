'''统一业务单据编号自动生成工具。
规则：前缀 + 日期(YYYYMMDD) + 秒级时间(HHMMSS) + 3位随机，保证同前缀下基本不冲突且可读。
仅在字段为空时生成，兼容既有手填数据。
'''
import random
from datetime import datetime


def gen_no(prefix='NO'):
    '''生成单据编号，如 HT20260912143005123'''
    now = datetime.now()
    date_part = now.strftime('%Y%m%d')
    time_part = now.strftime('%H%M%S')
    rand = '%03d' % random.randint(0, 999)
    return '%s%s%s%s' % (prefix, date_part, time_part, rand)


def ensure_no(instance, field, prefix):
    '''字段为空则生成编号写入，已存在保持不变；带碰撞重试。'''
    current = getattr(instance, field, '')
    if current:
        return current
    model = type(instance)
    candidate = gen_no(prefix)
    for _ in range(5):
        if not model.objects.filter(**{field: candidate}).exists():
            break
        candidate = gen_no(prefix)
    setattr(instance, field, candidate)
    return candidate
