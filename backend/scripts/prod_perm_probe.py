"""生产环境真实账号权限自测（2026-10-30）

用 curl + --resolve 走域名 SNI（直连 IP 会触发 Caddy 的 TLS 拒绝）。
流程：BOSS 建 2 个临时账号（运营部员工 / 运营部主管）→ 逐项验证 → 清理
"""
import json
import subprocess
import sys

BASE = "https://yuncaishuitong.com"
RESOLVE = "--resolve yuncaishuitong.com:443:140.143.85.54"
BOSS = ("luosifu", "LsfpLp27LhdsbDJF!")


def curl(path, token=None, method="GET", body=None):
    cmd = ["curl", "-sk", *RESOLVE.split(), BASE + path, "-X", method,
           "-H", "Content-Type: application/json"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out[:300]}


def login(u, p):
    r = curl("/api/accounts/auth/login/", method="POST", body={"username": u, "password": p})
    return (r.get("data") or {}).get("access"), (r.get("data") or {}).get("user")


def total(path, token):
    r = curl(path + ("&" if "?" in path else "?") + "page_size=1", token=token)
    if isinstance(r, dict) and "count" in r:
        return r["count"]
    d = r.get("data")
    if isinstance(d, list):
        return len(d)
    if isinstance(d, dict):
        return d.get("count")
    return None


def main():
    tok, user = login(*BOSS)
    if not tok:
        print("BOSS 登录失败"); return 1
    print(f"BOSS 登录 OK: {user.get('display_name')} / {user.get('role')} / {user.get('department_name')}")

    created = []
    try:
        # 建立临时主管（运营部）+ 临时员工（运营部）
        specs = [
            ("perm_p2_mgr", "运营部主管自测", 3, "MANAGER", "REGULAR"),
            ("perm_p2_emp", "运营部员工自测", 3, "EMPLOYEE", "REGULAR"),
        ]
        for uname, dname, dept, role, status in specs:
            r = curl("/api/accounts/users/", token=tok, method="POST", body={
                "username": uname, "display_name": dname, "phone": "139" + str(abs(hash(uname)) % 100000000).zfill(8),
                "department": dept, "role": role, "status": status,
                "password": "Probe!2345", "password2": "Probe!2345",
            })
            if r.get("id") or (r.get("data") or {}).get("id"):
                uid = r.get("id") or r["data"]["id"]
                created.append(uid)
                print(f"  建账号 {uname} id={uid} OK")
            else:
                print(f"  建账号 {uname} 失败: {str(r)[:260]}")

        if len(created) < 2:
            print("临时账号创建未达预期，终止测试"); return 1

        mgr_tok, mgr_u = login("perm_p2_mgr", "Probe!2345")
        emp_tok, emp_u = login("perm_p2_emp", "Probe!2345")
        print(f"主管登录: {bool(mgr_tok)} 员工登录: {bool(emp_tok)}")

        print("\n=== A. 部门业绩：向上汇总 & 越权 ===")
        endpoints = [
            ("/api/dashboard/company-performance/", "BOSS", tok),
            ("/api/dashboard/company-performance/", "主管", mgr_tok),
            ("/api/dashboard/company-performance/", "员工", emp_tok),
        ]
        for path, label, t in endpoints:
            if not t:
                continue
            r = curl(path + "?month=2026-10", token=t)
            d = r if isinstance(r, dict) else {}
            print(f"  {label:4s} scope={d.get('scope')} 部门数={len(d.get('departments') or [])} "
                  f"排行={len(d.get('top_performers') or [])}")

        print("\n=== B. 跨部门访问部门看板 ===")
        for code in ("SALES", "ACCOUNT", "OPS", "MGMT"):
            a = curl(f"/api/dashboard/department/{code}/?month=2026-10", token=tok)
            b = curl(f"/api/dashboard/department/{code}/?month=2026-10", token=mgr_tok) if mgr_tok else {}
            c = curl(f"/api/dashboard/department/{code}/?month=2026-10", token=emp_tok) if emp_tok else {}
            code_of = lambda r: r.get("code") if isinstance(r, dict) else "?"
            print(f"  {code:8s} BOSS={code_of(a)}  主管={code_of(b)}  员工={code_of(c)}")

        print("\n=== C. 部门员工明细（不该给普通员工）===")
        for label, t in (("主管", mgr_tok), ("员工", emp_tok)):
            if not t:
                continue
            for code in ("OPS", "SALES"):
                r = curl(f"/api/dashboard/department/{code}/members/?month=2026-10", token=t)
                code_of = r.get("code") if isinstance(r, dict) else "?"
                n = len((r.get("data") or [])) if isinstance(r, dict) and isinstance(r.get("data"), list) else 0
                print(f"  {label} {code:8s} -> code={code_of} 成员={n}")

        print("\n=== D. 业务数据可见条数（BOSS / 主管 / 员工）===")
        eps = ["/api/sales/leads/", "/api/sales/customers/", "/api/sales/call-records/",
               "/api/accounting/clients/", "/api/accounting/monthly-tasks/",
               "/api/reports/daily-reports/", "/api/growth/leads/", "/api/common/op-logs/"]
        print(f"  {'接口':34s}{'BOSS':>8s}{'主管':>8s}{'员工':>8s}")
        for ep in eps:
            print(f"  {ep:34s}{str(total(ep, tok)):>8s}"
                  f"{str(total(ep, mgr_tok) if mgr_tok else '-'):>8s}"
                  f"{str(total(ep, emp_tok) if emp_tok else '-'):>8s}")

    finally:
        print("\n=== E. 清理临时账号 ===")
        for uid in created:
            r = curl(f"/api/accounts/users/{uid}/", token=tok, method="PATCH",
                     body={"is_active": False, "status": "RESIGNED"})
            print(f"  停用 id={uid}: {'OK' if isinstance(r, dict) and r.get('id') else str(r)[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
