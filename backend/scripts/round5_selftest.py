"""第五轮增量自测：菜单分组 / 线索分配到个人 / 合同订单下发外勤

用法：venv/bin/python scripts/round5_selftest.py
覆盖：
  1. 知识库管理菜单归属（静态检查 router/index.js）
  2. 管理层分配线索 -> 个人（in_pool 置否 + 公海记录关闭 + LeadFlow 留痕）
  3. 合同订单下发外勤（创建即指定 assignee -> 派单人 + 「订单下发」留痕）
  4. 未指定外勤的旧用法保持原样（PENDING、无派单人、无下发留痕）
全部造数据在测试后物理清理，不污染本地库。
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

from apps.accounts.models import User  # noqa: E402
from apps.growth.models import (  # noqa: E402
    FieldProgress, FieldTask, GrowthRole, LeadChannel, LeadExt, LeadFlow, LeadPool,
)
from apps.sales.models import Lead  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, extra=""):
    (PASS if ok else FAIL).append(name)
    print(("  [OK]   " if ok else "  [FAIL] ") + name + (("  -> " + str(extra)) if extra else ""))


def router_text():
    p = os.path.join(BASE_DIR, "..", "web", "src", "router", "index.js")
    with open(os.path.abspath(p), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- 1. 菜单分组
print("\n== 1. 知识库管理菜单归属 ==")
txt = router_text()
lines = [ln for ln in txt.splitlines() if "知识库管理" in ln and "path:" in ln]
check("知识库管理路由有且只有一条", len(lines) == 1, len(lines))
if lines:
    check("分组为「入职与成长」", "group: '入职与成长'" in lines[0], lines[0].strip()[:110])
    check("已不在「运营部」分组", "group: '运营部'" not in lines[0])
idx_know = txt.find("知识库管理")
idx_group_head = txt.find("第一梯队：入职与成长")
idx_sec2 = txt.find("第二梯队：业务部门")
check("声明位置落在入职与成长代码块内", idx_group_head < idx_know < idx_sec2)

# ------------------------------------------------- 2. 管理层分配线索到个人
print("\n== 2. 管理层分配线索到个人 ==")
boss = User.objects.filter(is_active=True).filter(role="BOSS").first() or \
    User.objects.filter(is_active=True, is_superuser=True).first()
ops_user = None
closer_user = None
for r in GrowthRole.objects.filter(role="OPS").select_related("user"):
    if r.user and r.user.is_active:
        ops_user = r.user
        break
for r in GrowthRole.objects.filter(role="CLOSER").select_related("user"):
    if r.user and r.user.is_active:
        closer_user = r.user
        break
if ops_user is None:
    ops_user = User.objects.filter(is_active=True).exclude(id=boss.id).first()
if closer_user is None:
    closer_user = User.objects.filter(is_active=True).exclude(
        id__in=[boss.id, ops_user.id]).first()

print(f"  账号：BOSS={boss.username}({boss.id}) 运营={ops_user.username} 承接={closer_user.username}")

lead = Lead.objects.create(name="自测-线索分配", phone="19900000001", created_by=boss)
channel = LeadChannel.objects.filter(is_deleted=False).first()
ext = LeadExt.objects.create(lead=lead, channel=channel, in_pool=True, created_by=boss,
                             source_account_no="TEST-ACC", contact_type="PHONE",
                             contact_value="19900000001")
pool = LeadPool.objects.create(lead_ext=ext, status="WAITING", created_by=boss)

c = APIClient()
c.force_authenticate(user=boss)
resp = c.post(f"/api/growth/leads/{ext.id}/assign/",
              {"owner_id": ops_user.id, "closer_id": closer_user.id,
               "remark": "自测：分配至个人"}, format="json")
check("分配接口返回 200", resp.status_code == 200, resp.status_code)
ext.refresh_from_db()
pool.refresh_from_db()
check("归属运营已落到个人", ext.ops_owner_id == ops_user.id, ext.ops_owner_id)
check("承接人已落到个人", ext.closer_id == closer_user.id, ext.closer_id)
check("线索已移出公海", ext.in_pool is False, ext.in_pool)
check("公海记录 WAITING -> CLAIMED", pool.status == "CLAIMED", pool.status)
flows = LeadFlow.objects.filter(lead_ext=ext, action="ASSIGN")
check("已写入 ASSIGN 流转记录", flows.count() == 1, flows.count())
if flows.exists():
    f = flows.first()
    check("流转记录含操作人与接收人",
          f.from_user_id is not None and f.to_user_id in (ops_user.id, closer_user.id),
          f"{f.from_user_id}->{f.to_user_id}")
# 空选校验
resp2 = c.post(f"/api/growth/leads/{ext.id}/assign/", {"remark": "空"}, format="json")
check("不选任何人时返回 400 且提示", resp2.status_code == 400, resp2.status_code)
# 不越权：普通员工不可分配
role_uid = set(GrowthRole.objects.values_list("user_id", flat=True))
emp = User.objects.filter(is_active=True, role="EMPLOYEE", is_superuser=False) \
    .exclude(id__in=role_uid).exclude(id__in=[boss.id, ops_user.id, closer_user.id]).first()
if emp:
    c2 = APIClient()
    c2.force_authenticate(user=emp)
    r3 = c2.post(f"/api/growth/leads/{ext.id}/assign/",
                 {"owner_id": ops_user.id}, format="json")
    check(f"普通员工({emp.username})不可分配（403/404）", r3.status_code in (403, 404), r3.status_code)

# --------------------------------------------- 3. 合同订单下发外勤
print("\n== 3. 合同订单下发外勤 ==")
payload = {
    "title": "自测-某公司 · 工商注册",
    "customer_name": "自测-某公司",
    "customer_type": "ENTERPRISE",
    "business_type": "REGISTER",
    "task_type": "工商注册",
    "from_order_no": "HT-TEST-0001",
    "assignee": closer_user.id,          # 下发目标外勤人员
    "remark": "自测：订单下发",
}
r = c.post("/api/growth/field-tasks/", payload, format="json")
check("下发创建返回 201", r.status_code == 201, r.status_code)
task_id = (r.data or {}).get("id") if hasattr(r, "data") else None
if not task_id:
    body = r.json() if hasattr(r, "json") else {}
    task_id = body.get("id")
task = FieldTask.objects.filter(id=task_id).first()
check("任务已生成并自动编号 WD", bool(task and task.task_no.startswith("WD")),
      task.task_no if task else None)
if task:
    check("已记录下发目标外勤", task.assignee_id == closer_user.id, task.assignee_id)
    check("已记录派单人（下发人）", task.assigned_by_id == boss.id, task.assigned_by_id)
    check("来源单号已回写", task.from_order_no == "HT-TEST-0001", task.from_order_no)
    check("状态仍为待接收（外勤需接单）", task.status == "PENDING", task.status)
    prog = FieldProgress.objects.filter(task=task, node="订单下发")
    check("已写入「订单下发」留痕", prog.count() == 1, prog.count())
    check("节点模板已自动生成",
          task.nodes.filter(is_deleted=False).count() > 0,
          task.nodes.filter(is_deleted=False).count())

# --------------------------------------------- 4. 旧用法回归（不选外勤）
print("\n== 4. 旧用法回归：不指定外勤 ==")
payload2 = dict(payload)
payload2.pop("assignee")
payload2["title"] = "自测-旧用法"
r2 = c.post("/api/growth/field-tasks/", payload2, format="json")
check("创建返回 201", r2.status_code == 201, r2.status_code)
body2 = r2.json() if hasattr(r2, "json") else {}
t2 = FieldTask.objects.filter(id=body2.get("id")).first()
if t2:
    check("无派单目标时 assignee 为空", t2.assignee_id is None, t2.assignee_id)
    check("无派单目标时不写派单人", t2.assigned_by_id is None, t2.assigned_by_id)
    check("进入公共待接收池", t2.status == "PENDING", t2.status)
    check("不产生「订单下发」留痕",
          FieldProgress.objects.filter(task=t2, node="订单下发").count() == 0)

# ---------------------------------------------------------------- 清理
print("\n== 清理自测数据 ==")
FieldProgress.objects.filter(task__title__startswith="自测-").delete()
FieldTask.objects.filter(title__startswith="自测-").delete()
LeadFlow.objects.filter(lead_ext__lead__name__startswith="自测-").delete()
LeadPool.objects.filter(lead_ext__lead__name__startswith="自测-").delete()
LeadExt.objects.filter(lead__name__startswith="自测-").delete()
Lead.objects.filter(name__startswith="自测-").delete()
print("  已清理临时线索 / 外勤任务 / 流转记录")

print("\n================ 汇总 ================")
print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    for f in FAIL:
        print("  失败：", f)
    sys.exit(1)
