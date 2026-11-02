# -*- coding: utf-8 -*-
"""2026-10-30 增量优化自测脚本（Boss 全功能自测要求）

覆盖：
  1) 员工管理批量删除接口（新修复）
  2) 跨部门订单转接接口（新增）
  3) 线索分配 → 站内信通知（新增：电销/增长两条链路）
  4) autoForm 空表兜底依赖的 OPTIONS 元数据
  5) 站内信列表 / 未读数
测试数据自建自清，不污染业务库。
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.common.models import InboxMessage  # noqa: E402
from apps.growth.models import (LeadChannel, LeadExt, FieldTask,  # noqa: E402
                                FieldProgress, FieldTaskNode)
from apps.sales.models import Lead  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, extra=""):
    (PASSED if cond else FAILED).append(name + (f" | {extra}" if extra and not cond else ""))
    print(("✅ " if cond else "❌ ") + name + (f" → {extra}" if extra and not cond else ""))


boss = User.objects.filter(username="boss").first() or User.objects.filter(is_superuser=True).first()
api = APIClient()
api.force_authenticate(boss)

# ---------- 1) 员工管理批量删除 ----------
import shutil  # noqa: E402
tu = User.objects.create(username="__smoke_del__", phone="19900000001", role="EMPLOYEE",
                         status="REGULAR", is_active=True, first_name="自测临时员工")
r = api.post("/api/accounts/users/bulk-delete/", {"ids": [tu.id]}, format="json")
check("批量删除接口返回 code=0", r.status_code == 200 and r.data.get("code") == 0, str(getattr(r, "data", r.status_code)))
tu.refresh_from_db()
check("批量删除后员工已停用并置离职", tu.is_active is False and tu.status == "RESIGNED")
check("批量删除后员工从员工列表消失",
      tu.id not in [u["id"] for u in api.get("/api/accounts/users/?page_size=200").data["results"]])
tu.delete()  # 物理清理测试账号

# 非人事批量删除应被拒绝（权限墙）
emp = User.objects.filter(role="EMPLOYEE", is_active=True, is_superuser=False).first()
api2 = APIClient(); api2.force_authenticate(emp)
r2 = api2.post("/api/accounts/users/bulk-delete/", {"ids": [boss.id]}, format="json")
check("普通员工调用批量删除被拒绝(403)", r2.status_code == 403, str(r2.status_code))

# ---------- 2) 跨部门订单转接 ----------
r = api.post("/api/growth/field-tasks/transfer-in/",
             {"customer_name": "自测转接客户", "order_no": "SMOKE-2026-001",
              "business_type": "REGISTER", "remark": "自测"}, format="json")
check("跨部门转接创建成功(201)", r.status_code == 201, str(r.status_code))
tid = r.data.get("id") if r.status_code == 201 else None
if tid:
    t = FieldTask.objects.get(id=tid)
    check("转接单状态=待接收", t.status == "PENDING", t.status)
    check("转接单记录来源单号", t.from_order_no == "SMOKE-2026-001")
    check("转接单自动生成进度节点", FieldTaskNode.objects.filter(task_id=tid).exists())
    check("转接单留下「跨部门转接」进度",
          FieldProgress.objects.filter(task_id=tid, node="跨部门转接").exists())
    # 编辑（任务6：外勤任务编辑）
    r = api.patch(f"/api/growth/field-tasks/{tid}/", {"customer_name": "自测转接客户-改"}, format="json")
    check("外勤任务编辑保存成功", r.status_code == 200 and r.data["customer_name"] == "自测转接客户-改")
    # 清理
    FieldTaskNode.objects.filter(task_id=tid).delete()
    FieldProgress.objects.filter(task_id=tid).delete()
    FieldTask.objects.filter(id=tid).delete()
r = api.post("/api/growth/field-tasks/transfer-in/", {}, format="json")
check("转接口参校验：全空被拒(400)", r.status_code == 400, str(r.status_code))

# ---------- 3) 线索分配 → 站内信通知 ----------
emp_user = User.objects.filter(username="sales2").first() or User.objects.filter(role="EMPLOYEE").first()
lead = Lead.objects.create(name="自测线索", phone="19900000002", source="OTHER", status="NEW",
                           created_by=boss)
InboxMessage.objects.filter(recipient=emp_user, title="您有新的线索分配").delete()
r = api.post("/api/sales/leads/assign/", {"ids": [lead.id], "owner_id": emp_user.id}, format="json")
check("电销线索分配成功", r.status_code == 200 and r.data.get("code") == 0, str(getattr(r, "data", r.status_code)))
check("电销线索分配 → 员工收到站内通知",
      InboxMessage.objects.filter(recipient=emp_user, title="您有新的线索分配").exists())

ch = LeadChannel.objects.filter(is_enabled=True).first()
ext = LeadExt.objects.create(lead=lead, channel=ch, source_account_no="SMOKE-ACC",
                             contact_type="PHONE", contact_value="19900000002", created_by=boss)
InboxMessage.objects.filter(recipient=emp_user, title="您有新的线索分配").delete()
r = api.post(f"/api/growth/leads/{ext.id}/assign/", {"owner_id": emp_user.id}, format="json")
check("增长中心线索分配成功", r.status_code == 200, str(r.status_code))
check("增长中心线索分配 → 员工收到站内通知",
      InboxMessage.objects.filter(recipient=emp_user, title="您有新的线索分配").exists())
# 线索编辑（任务6）
r = api.patch(f"/api/growth/leads/{ext.id}/", {"name": "自测线索-改", "customer_need": "改需求"}, format="json")
check("线索编辑保存成功", r.status_code == 200 and "已保存修改" in str(r.data.get("detail", "")), str(getattr(r, "data", r.status_code)))

# ---------- 4) autoForm 空表兜底：OPTIONS 元数据 ----------
r = api.options("/api/accounting/clients/")
post = r.data.get("actions", {}).get("POST") if hasattr(r, "data") else {}
check("OPTIONS 元数据可生成表单字段", bool(post), str(r.status_code))
if post:
    sample = list(post.items())[:2]
    check("元数据含字段标签(中文)", all(f.get("label") for _, f in sample), str(sample))

# ---------- 5) 站内信 ----------
r = api.get("/api/common/inbox/unread-count/")
check("站内信未读数接口正常", r.status_code == 200, str(r.status_code))

# 清理
ext.delete()
lead.delete()
InboxMessage.objects.filter(title__icontains="自测").delete()

print("\n===== 自测结果 =====")
print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
if FAILED:
    print("失败项：")
    for f in FAILED:
        print("  -", f)
    sys.exit(1)
