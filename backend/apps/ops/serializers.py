"""运营部：序列化器"""
from rest_framework import serializers
from .models import (
    AdPlatform, AdAccount, AdCampaign, AdDailyStat, AdCreative,
    ContentPost, ContentStat, ChannelBudget, OpsDailyReport, CostRecord,
)


class AdPlatformSerializer(serializers.ModelSerializer):
    """投放平台"""
    code_name = serializers.CharField(source="get_code_display", read_only=True)
    account_count = serializers.SerializerMethodField()

    class Meta:
        model = AdPlatform
        fields = ["id", "name", "code", "code_name", "login_url", "account_name",
                  "contact", "contact_phone", "has_api", "remark",
                  "account_count", "created_at", "updated_at"]
        read_only_fields = ["account_count", "created_at", "updated_at"]

    def get_account_count(self, obj):
        return obj.accounts.filter(is_deleted=False).count()


class AdAccountSerializer(serializers.ModelSerializer):
    """广告账户"""
    platform_name = serializers.CharField(source="platform.name", read_only=True)
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AdAccount
        fields = ["id", "platform", "platform_name", "name", "account_id", "owner",
                  "owner_name", "daily_budget", "month_budget", "balance",
                  "status", "status_name", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class AdCampaignSerializer(serializers.ModelSerializer):
    """推广计划"""
    account_name = serializers.CharField(source="account.name", read_only=True)
    platform_name = serializers.CharField(source="account.platform.name", read_only=True)

    class Meta:
        model = AdCampaign
        fields = ["id", "account", "account_name", "platform_name", "name", "campaign_id",
                  "goal", "biz_line", "city", "start_date", "end_date", "status",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class AdDailyStatSerializer(serializers.ModelSerializer):
    """每日投放数据"""
    platform_name = serializers.CharField(source="platform.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    cpl = serializers.ReadOnlyField()
    cac = serializers.ReadOnlyField()
    roi = serializers.ReadOnlyField()
    lead_valid_rate = serializers.ReadOnlyField()

    class Meta:
        model = AdDailyStat
        fields = ["id", "platform", "platform_name", "account", "account_name",
                  "campaign", "campaign_name", "date", "cost", "impression", "click",
                  "cost_input", "click_rate", "avg_click_cost", "lead_count", "valid_lead",
                  "phone_added", "wechat_added", "visit_count", "deal_count", "deal_amount",
                  "cpl", "cac", "roi", "lead_valid_rate",
                  "operator", "operator_name", "remark", "created_at"]
        read_only_fields = ["created_at"]


class AdCreativeSerializer(serializers.ModelSerializer):
    """投放素材"""
    platform_name = serializers.CharField(source="platform.name", read_only=True)
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = AdCreative
        fields = ["id", "platform", "platform_name", "name", "kind", "kind_name",
                  "file", "copy", "link", "cost", "lead_count", "impression", "online",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ContentPostSerializer(serializers.ModelSerializer):
    """内容作品"""
    platform_name = serializers.CharField(source="get_platform_display", read_only=True)
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = ContentPost
        fields = ["id", "platform", "platform_name", "kind", "kind_name", "title",
                  "topic", "author", "author_name", "publish_at", "link", "cover",
                  "script", "status", "status_name", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ContentStatSerializer(serializers.ModelSerializer):
    """内容数据"""
    post_title = serializers.CharField(source="post.title", read_only=True)

    class Meta:
        model = ContentStat
        fields = ["id", "post", "post_title", "stat_date", "view", "like", "comment",
                  "share", "collect", "follow", "private_msg", "lead_count"]


class ChannelBudgetSerializer(serializers.ModelSerializer):
    """渠道预算"""
    platform_name = serializers.CharField(source="platform.name", read_only=True)

    class Meta:
        model = ChannelBudget
        fields = ["id", "month", "platform", "platform_name", "budget",
                  "lead_target", "deal_target", "remark", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OpsDailyReportSerializer(serializers.ModelSerializer):
    """运营日报"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = OpsDailyReport
        fields = ["id", "user", "user_name", "date", "total_cost", "total_lead",
                  "total_wechat", "total_deal", "highlights", "problems",
                  "tomorrow_plan", "attachments", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


# ============== 主播板块：获客日报 / 留资台账 / 直播投流 ==============
from .models import AnchorDailyReport, LeadLedger, AnchorAdStat


class AnchorDailyReportSerializer(serializers.ModelSerializer):
    """主播获客日报"""
    channel_type_name = serializers.CharField(source="get_channel_type_display", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    enter_rate = serializers.ReadOnlyField()

    class Meta:
        model = AnchorDailyReport
        fields = ["id", "channel_type", "channel_type_name", "date", "anchor_name",
                  "operator", "operator_name",
                  "cost", "lead_count", "valid_lead", "acquisition_cost",
                  "account_setup", "product_content",
                  "exposure", "enter_room", "enter_rate", "avg_online", "avg_stay",
                  "live_duration", "live_cost", "live_lead", "live_valid_lead", "lead_cost",
                  "remark", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class LeadLedgerSerializer(serializers.ModelSerializer):
    """客户留资明细台账"""
    channel_name = serializers.CharField(source="get_channel_display", read_only=True)
    follower_name = serializers.CharField(source="follower.display_name", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    is_passed_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadLedger
        fields = ["id", "channel", "channel_name", "date", "customer_name", "contact",
                  "need", "address", "follower", "follower_name", "is_passed",
                  "is_passed_name", "detail", "operator", "operator_name",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def get_is_passed_name(self, obj):
        return "通过" if obj.is_passed else "未通过"


class AnchorAdStatSerializer(serializers.ModelSerializer):
    """直播投流数据"""
    ad_type_name = serializers.CharField(source="get_ad_type_display", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    lead_cost = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()

    class Meta:
        model = AnchorAdStat
        fields = ["id", "ad_type", "ad_type_name", "date", "platform",
                  "operator", "operator_name",
                  "cost", "impression", "click", "click_rate",
                  "private_msg", "lead_count", "lead_cost", "remark",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class CostRecordSerializer(serializers.ModelSerializer):
    """运营成本记录"""
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    platform_name = serializers.CharField(source="platform.name", read_only=True, default="")
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True, default="")

    class Meta:
        model = CostRecord
        fields = ["id", "date", "category", "category_label", "platform", "platform_name",
                  "name", "amount", "remark", "created_by", "created_by_name", "created_at"]
        read_only_fields = ["created_by", "created_at"]
