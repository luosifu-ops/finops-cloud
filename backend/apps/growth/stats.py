"""增长中心：全维度投放数据统计（纯新增页面模块的数据源）

统计维度双并行：个人数据 + 部门整体数据
核心指标：各平台线索数量 / 投放消耗成本 / 投产比 / 个人转化率 / 部门转化率 / 平台产出对比

【高级版】在基础版之上加：
  1. CPA（单成交获取成本）+ CPL 显式别名 + 综合产出指数（无量纲分）
  2. 环比（MoM）：与上一同长度窗口对比线索 / 成交 / 成本 变化率
  3. MLP 投产比预测接入预留位（predicted_roi / confidence）—— 待后续接 XGBoost/LightGBM
"""
from datetime import timedelta

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LeadChannel, LeadExt, AdSpendRecord, LeadPool
from .permissions import can_view_all


# ============================================================
# 工具：日期窗口 + 安全除法
# ============================================================

def _date_range(request):
    """解析日期范围，默认近 30 天"""
    end = request.query_params.get("end")
    start = request.query_params.get("start")
    if start and end:
        return start, end
    today = timezone.localdate()
    return str(today - timedelta(days=30)), str(today)


def _prev_window(start, end):
    """返回与 [start, end] 等长度的上一窗口 [prev_start, prev_end]

    例：start=2026-08-06, end=2026-09-04（30 天）
       prev_start=2026-07-07, prev_end=2026-08-05（30 天）
    """
    s = timezone.datetime.strptime(start, "%Y-%m-%d").date()
    e = timezone.datetime.strptime(end, "%Y-%m-%d").date()
    length = (e - s).days + 1
    prev_end = s - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    return str(prev_start), str(prev_end)


def _safe_div(a, b, default=0.0):
    """安全除法，b 为 0 时返回 default（保留两位小数）"""
    if not b:
        return default
    try:
        return round(float(a) / float(b), 4)
    except (TypeError, ZeroDivisionError):
        return default


def _is_deal_q():
    """成交判定：3570 标记为 0成交，或原线索状态为已成交"""
    return Q(stage_3570="S0") | Q(lead__status="DEAL")


def _production_score(lead_count, deal_count, cost):
    """综合产出指数（无量纲，分数越高越好）

    设计：
      - 线索基础分：lead_count / 10    （1 条线索 0.1 分，满 100 条为 1 分）
      - 成交权重：  deal_count * 5      （成交权重远高于线索，区分 ROI 质变）
      - 成本控制：  1 / max(cost, 1)    （成本越低分数越高，呈反比）
      - 最终：      (线索分 + 成交分) / log10(成本+10)
                    用对数抑制大额消费对小成本的过度惩罚
    """
    base = (lead_count / 10.0) + (deal_count * 5.0)
    import math
    denom = math.log10(max(float(cost), 0) + 10.0)
    score = base / denom if denom > 0 else base
    return round(score, 2)


def _predicted_roi_placeholder(lead_count, deal_count, cost):
    """【MLP 接入预留点】投产比预测

    当前实现：基于近期趋势的启发式占位。
    后续替换：调用已训练好的 XGBoost / LightGBM 模型，输入：
      - lead_count  deal_count  cost
      - lead_count 的近 7/14/30 日滑动均值
      - 成交时间分布 / 平台特征编码
    返回：predicted_roi（float），confidence（float 0-1）

    启发式公式（v0）：
      predicted_roi = real_roi × 衰减系数（lead_count 越多越稳）
      confidence    = sigmoid(lead_count / 50)（样本越多置信度越高）
    """
    real_roi = _safe_div(deal_count, cost, 0.0)
    decay = min(1.0, 0.4 + 0.6 * (lead_count / 100.0))
    # sigmoid 简易版
    confidence = round(1.0 / (1.0 + 2.71828 ** (-lead_count / 50.0)), 3)
    return round(real_roi * decay, 4), confidence


def _mom_change(cur, prev):
    """计算环比变化率（prev=0 时返回 None 表示基期无数据）"""
    if not prev:
        return None
    try:
        return round(((float(cur) - float(prev)) / float(prev)) * 100, 2)
    except (TypeError, ZeroDivisionError):
        return None


def _pack_metrics(lead_count, deal_count, cost):
    """统一封装高级指标（含 CPL/CPA/产出分/MoM/MLP 预留）

    输入：当前窗口 lead / deal / cost
    返回：在原基础字段之上补充：
        cpl, cpa, production_score, predicted_roi, confidence
    环比字段（mom_*）由调用方在双窗口数据齐了之后再组装。
    """
    return {
        "cpl": _safe_div(cost, lead_count),         # 单条线索成本（已有 cost_per_lead 的语义别名）
        "cpa": _safe_div(cost, deal_count),         # 单个成交客户获取成本
        "production_score": _production_score(lead_count, deal_count, cost),
        "predicted_roi": None,                      # MLP 预测（默认 None，由调用方填）
        "confidence": None,                          # 预测置信度（默认 None）
    }


# ============================================================
# 视图集
# ============================================================

class GrowthStatsViewSet(viewsets.ViewSet):
    """投放数据统计面板"""

    # ---------- 总览：个人 + 部门 双维度（含高级指标 + MoM） ----------
    @action(detail=False, methods=["get"])
    def overview(self, request):
        start, end = _date_range(request)
        prev_start, prev_end = _prev_window(start, end)
        user = request.user
        all_view = can_view_all(user)

        base = LeadExt.objects.filter(
            is_deleted=False, created_at__date__range=[start, end])
        prev_base = LeadExt.objects.filter(
            is_deleted=False, created_at__date__range=[prev_start, prev_end])

        # 部门整体（全部数据）
        dept_qs = base if all_view else base.filter(
            Q(ops_owner=user) | Q(closer=user)).distinct()
        prev_dept_qs = prev_base if all_view else prev_base.filter(
            Q(ops_owner=user) | Q(closer=user)).distinct()
        dept_total = dept_qs.count()
        dept_deal = dept_qs.filter(_is_deal_q()).count()

        dept_spend = AdSpendRecord.objects.filter(
            is_deleted=False, stat_date__range=[start, end])
        prev_dept_spend = AdSpendRecord.objects.filter(
            is_deleted=False, stat_date__range=[prev_start, prev_end])
        if not all_view:
            dept_spend = dept_spend.filter(owner=user)
            prev_dept_spend = prev_dept_spend.filter(owner=user)
        dept_cost = dept_spend.aggregate(s=Sum("cost"))["s"] or 0
        prev_dept_total = prev_dept_qs.count()
        prev_dept_deal = prev_dept_qs.filter(_is_deal_q()).count()
        prev_dept_cost = prev_dept_spend.aggregate(s=Sum("cost"))["s"] or 0

        # 个人（仅自己录入的）
        my_qs = base.filter(ops_owner=user)
        prev_my_qs = prev_base.filter(ops_owner=user)
        my_total = my_qs.count()
        my_deal = my_qs.filter(_is_deal_q()).count()

        my_spend = AdSpendRecord.objects.filter(
            is_deleted=False, stat_date__range=[start, end], owner=user)
        prev_my_spend = AdSpendRecord.objects.filter(
            is_deleted=False, stat_date__range=[prev_start, prev_end], owner=user)
        my_cost = my_spend.aggregate(s=Sum("cost"))["s"] or 0
        prev_my_total = prev_my_qs.count()
        prev_my_deal = prev_my_qs.filter(_is_deal_q()).count()
        prev_my_cost = prev_my_spend.aggregate(s=Sum("cost"))["s"] or 0

        def _pack(total, deal, cost, prev_total, prev_deal, prev_cost):
            base_pack = {
                "lead_count": total,
                "deal_count": deal,
                "cost": float(cost),
                "cost_per_lead": round(float(cost) / total, 2) if total else 0,
                "convert_rate": round(deal / total * 100, 2) if total else 0,
                "roi": round(deal / float(cost), 4) if cost else 0,
            }
            base_pack.update(_pack_metrics(total, deal, cost))
            # 环比（基期 0 时返回 None）
            base_pack["mom_lead_change"] = _mom_change(total, prev_total)
            base_pack["mom_deal_change"] = _mom_change(deal, prev_deal)
            base_pack["mom_cost_change"] = _mom_change(cost, prev_cost)
            # MLP 预测（沿用同窗口数据）
            pred_roi, conf = _predicted_roi_placeholder(total, deal, cost)
            base_pack["predicted_roi"] = pred_roi
            base_pack["confidence"] = conf
            return base_pack

        return Response({
            "range": {"start": start, "end": end,
                      "prev_start": prev_start, "prev_end": prev_end},
            "scope": "all" if all_view else "personal",
            "dept": _pack(dept_total, dept_deal, dept_cost,
                          prev_dept_total, prev_dept_deal, prev_dept_cost),
            "my": _pack(my_total, my_deal, my_cost,
                         prev_my_total, prev_my_deal, prev_my_cost),
        })

    # ---------- 各平台产出对比（含高级指标 + MoM + MLP 预测） ----------
    @action(detail=False, methods=["get"])
    def by_platform(self, request):
        start, end = _date_range(request)
        prev_start, prev_end = _prev_window(start, end)
        user = request.user
        all_view = can_view_all(user)

        channels = LeadChannel.objects.filter(is_deleted=False).order_by("sort")
        rows = []
        for ch in channels:
            qs = LeadExt.objects.filter(
                is_deleted=False, channel=ch, created_at__date__range=[start, end])
            prev_qs = LeadExt.objects.filter(
                is_deleted=False, channel=ch, created_at__date__range=[prev_start, prev_end])
            if not all_view:
                qs = qs.filter(Q(ops_owner=user) | Q(closer=user)).distinct()
                prev_qs = prev_qs.filter(Q(ops_owner=user) | Q(closer=user)).distinct()

            lead_count = qs.count()
            deal_count = qs.filter(_is_deal_q()).count()
            prev_lead = prev_qs.count()
            prev_deal = prev_qs.filter(_is_deal_q()).count()

            spend = AdSpendRecord.objects.filter(
                is_deleted=False, channel=ch, stat_date__range=[start, end])
            prev_spend = AdSpendRecord.objects.filter(
                is_deleted=False, channel=ch, stat_date__range=[prev_start, prev_end])
            if not all_view:
                spend = spend.filter(owner=user)
                prev_spend = prev_spend.filter(owner=user)
            cost = spend.aggregate(s=Sum("cost"))["s"] or 0
            prev_cost = prev_spend.aggregate(s=Sum("cost"))["s"] or 0

            rate = round(deal_count / lead_count * 100, 2) if lead_count else 0
            # 产出分层：零产出 / 低产出 / 高产出 / 增长型（MoM lead > +20%）
            if lead_count == 0:
                level = "ZERO"
            elif deal_count == 0:
                level = "LOW"
            else:
                level = "HIGH"

            row = {
                "channel_id": ch.id,
                "code": ch.code,
                "name": ch.name,
                "lead_count": lead_count,
                "deal_count": deal_count,
                "cost": float(cost),
                "cost_per_lead": round(float(cost) / lead_count, 2) if lead_count else 0,
                "convert_rate": rate,
                "roi": round(deal_count / float(cost), 4) if cost else 0,
                "level": level,
                "level_label": {"ZERO": "零产出", "LOW": "低产出", "HIGH": "高产出"}[level],
            }
            # 高级指标
            row.update(_pack_metrics(lead_count, deal_count, cost))
            # 环比
            row["mom_lead_change"] = _mom_change(lead_count, prev_lead)
            row["mom_deal_change"] = _mom_change(deal_count, prev_deal)
            row["mom_cost_change"] = _mom_change(cost, prev_cost)
            # MLP 接入预留位
            pred_roi, conf = _predicted_roi_placeholder(lead_count, deal_count, cost)
            row["predicted_roi"] = pred_roi
            row["confidence"] = conf

            rows.append(row)

        # 按成交数降序，方便前端直接出图
        rows.sort(key=lambda r: (-r["deal_count"], -r["lead_count"]))
        summary = {
            "high": sum(1 for r in rows if r["level"] == "HIGH"),
            "low": sum(1 for r in rows if r["level"] == "LOW"),
            "zero": sum(1 for r in rows if r["level"] == "ZERO"),
        }
        return Response({
            "range": {"start": start, "end": end,
                      "prev_start": prev_start, "prev_end": prev_end},
            "summary": summary,
            "rows": rows,
            # 高级指标元信息（前端如需展示算法版本可读）
            "metrics_meta": {
                "version": "v1.0.0",
                "produced_at": timezone.now().isoformat(),
                "fields": {
                    "cpl": "单条线索获取成本 = cost/lead_count",
                    "cpa": "单个成交客户的获取成本 = cost/deal_count",
                    "production_score": "无量纲综合产出指数（线索+5×成交）/log10(成本+10)",
                    "predicted_roi": "投产比预测（MLP 接入预留点，当前为启发式占位）",
                    "confidence": "MLP 预测置信度（0-1）",
                    "mom_lead_change / mom_deal_change / mom_cost_change": "环比变化率（%）",
                },
            },
        })

    # ---------- 个人数据 ----------
    @action(detail=False, methods=["get"])
    def my(self, request):
        start, end = _date_range(request)
        user = request.user
        qs = LeadExt.objects.filter(
            is_deleted=False, ops_owner=user, created_at__date__range=[start, end])
        total = qs.count()
        deal = qs.filter(_is_deal_q()).count()
        by_stage = {}
        for key, label in LeadExt.STAGE_3570:
            by_stage[label] = qs.filter(stage_3570=key).count()

        # 高阶信息：高级指标 + 上一窗口对比
        prev_start, prev_end = _prev_window(start, end)
        prev_qs = LeadExt.objects.filter(
            is_deleted=False, ops_owner=user, created_at__date__range=[prev_start, prev_end])
        prev_total = prev_qs.count()
        prev_deal = prev_qs.filter(_is_deal_q()).count()

        metrics = _pack_metrics(total, deal, 0)
        metrics["mom_lead_change"] = _mom_change(total, prev_total)
        metrics["mom_deal_change"] = _mom_change(deal, prev_deal)

        return Response({
            "range": {"start": start, "end": end,
                      "prev_start": prev_start, "prev_end": prev_end},
            "lead_count": total,
            "deal_count": deal,
            "convert_rate": round(deal / total * 100, 2) if total else 0,
            "by_stage": by_stage,
            "metrics": metrics,
        })

    # ---------- 部门整体 ----------
    @action(detail=False, methods=["get"])
    def dept(self, request):
        start, end = _date_range(request)
        user = request.user
        all_view = can_view_all(user)
        base = LeadExt.objects.filter(
            is_deleted=False, created_at__date__range=[start, end])
        if not all_view:
            base = base.filter(Q(ops_owner=user) | Q(closer=user)).distinct()
        total = base.count()
        deal = base.filter(_is_deal_q()).count()

        # 按运营人维度拆分（谁录入得多、谁转化得好）
        owners = {}
        for ext in base.select_related("ops_owner"):
            key = ext.ops_owner_id or 0
            name = getattr(ext.ops_owner, "display_name", None) or (
                ext.ops_owner.username if ext.ops_owner else "未指派")
            item = owners.setdefault(key, {"owner": key, "owner_name": name,
                                           "lead_count": 0, "deal_count": 0})
            item["lead_count"] += 1
            if ext.stage_3570 == "S0" or (ext.lead and ext.lead.status == "DEAL"):
                item["deal_count"] += 1
        for v in owners.values():
            v["convert_rate"] = round(v["deal_count"] / v["lead_count"] * 100, 2) if v["lead_count"] else 0
            # 单人：补充综合产出分
            v["production_score"] = _production_score(v["lead_count"], v["deal_count"], 0)

        return Response({
            "range": {"start": start, "end": end},
            "lead_count": total,
            "deal_count": deal,
            "convert_rate": round(deal / total * 100, 2) if total else 0,
            "by_owner": sorted(owners.values(), key=lambda x: -x["lead_count"]),
        })

    # ---------- 公海概览 ----------
    @action(detail=False, methods=["get"])
    def pool(self, request):
        """公海待领取数量"""
        qs = LeadPool.objects.filter(is_deleted=False, status="WAITING")
        return Response({"waiting": qs.count()})
