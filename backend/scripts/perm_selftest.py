"""权限隔离自测：以不同角色遍历全部列表接口，检查 500 与跨部门可见性

用法：venv/bin/python scripts/perm_selftest.py
"""
import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient  # noqa: E402
from django.urls import get_resolver  # noqa: E402
from apps.accounts.models import User  # noqa: E402

ROLES = [
    ("boss_admin", 21),      # 生产 BOSS（本地若有）
    ("boss", 12),
    ("sales_mgr", 24),
    ("sales1_leader", 27),
    ("sales2_emp", 28),
    ("acc_mgr", 25),
    ("acc1_emp", 35),
]


def die(msg):
    print("  !!", msg)


def list_endpoints():
    """收集所有 /api/ 下的列表路由（去掉带 pk 的详情路由）"""
    out = set()

    def walk(patterns, prefix=""):
        for p in patterns:
            pat = (prefix + str(p.pattern)).replace("^", "").replace("$", "")
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns, pat)
            else:
                if not pat.startswith("api/"):
                    continue
                if "<" in pat or "(" in pat:
                    continue
                if any(x in pat for x in ("auth/", "token/", "schema", "docs", "pay/")):
                    continue
                out.add("/" + pat)

    walk(get_resolver().url_patterns)
    return sorted(out)


def users_by_id():
    return {u.id: u for u in User.objects.all()}


def main():
    eps = list_endpoints()
    print(f"共 {len(eps)} 个接口待检查\n")
    results = {}
    count_results = {}
    users = users_by_id()
    for label, uid in ROLES:
        u = users.get(uid)
        if not u:
            print(f"[skip] {label} id={uid} 不存在")
            continue
        c = APIClient()
        c.force_authenticate(user=u)
        codes = {}
        counts = {}
        errs = []
        for ep in eps:
            try:
                r = c.get(ep, {"page_size": 100})
                codes[ep] = r.status_code
                if r.status_code == 200:
                    try:
                        body = r.json()
                    except Exception:
                        body = None
                    if isinstance(body, dict):
                        if "count" in body:
                            counts[ep] = body.get("count")
                        elif isinstance(body.get("data"), list):
                            counts[ep] = len(body["data"])
                        elif isinstance(body.get("results"), list):
                            counts[ep] = len(body["results"])
                    elif isinstance(body, list):
                        counts[ep] = len(body)
                if r.status_code >= 500:
                    errs.append((ep, r.status_code, (r.content or b"")[:200]))
            except Exception as e:
                codes[ep] = "EXC"
                errs.append((ep, "EXC", str(e)[:200]))
        results[label] = codes
        count_results[label] = counts
        print(f"=== {label}（{u.display_name or u.username} / {u.role} / "
              f"{getattr(u.department, 'code', '-')}）===")
        bad = {k: v for k, v in codes.items() if v not in (200, 403, 404, 405)}
        if errs:
            for e in errs[:12]:
                die(f"{e[0]} -> {e[1]} {e[2]}")
        if bad:
            for k, v in list(bad.items())[:12]:
                die(f"{k} -> {v}")
        if not errs and not bad:
            print("  OK：全部接口无 5xx / 无异常状态码")
        print()

    # 跨角色对比：同一接口返回条数
    print("=== 数据条数对比（关键接口）===")
    # 自动挑出「至少一个角色返回了数据」的列表接口
    keys = sorted({ep for c in count_results.values() for ep, n in c.items() if n})
    print(f"{'接口':52s}" + "".join(f"{k[:11]:>13s}" for k in count_results))
    for ep in keys:
        row = f"{ep:52s}"
        for k in count_results:
            v = count_results[k].get(ep, "-")
            row += f"{str(v):>13s}"
        print(row)


if __name__ == "__main__":
    main()
