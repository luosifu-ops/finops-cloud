# 主播板块增量：获客日报 / 留资台账 / 直播投流
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0002_budget_approval'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnchorDailyReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='已删除')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('channel_type', models.CharField(choices=[('PAID', '渠道获客-付费投放'), ('LIVE', '直播获客'), ('LOCAL_PUSH', '本地推投流获客'), ('AI', 'AI获客'), ('SOCIAL', '视频号/小红书/闲鱼获客')], db_index=True, default='PAID', max_length=20, verbose_name='获客板块')),
                ('date', models.DateField(db_index=True, verbose_name='日期')),
                ('anchor_name', models.CharField(blank=True, max_length=100, verbose_name='主播/账号')),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='消耗(元)')),
                ('lead_count', models.IntegerField(default=0, verbose_name='线索数量')),
                ('valid_lead', models.IntegerField(default=0, verbose_name='有效线索')),
                ('acquisition_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='获客成本(元)')),
                ('account_setup', models.TextField(blank=True, verbose_name='账户搭建')),
                ('product_content', models.TextField(blank=True, verbose_name='产品内容')),
                ('exposure', models.IntegerField(default=0, verbose_name='直播曝光人数')),
                ('enter_room', models.IntegerField(default=0, verbose_name='直播进房人数')),
                ('avg_online', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='平均在线人数')),
                ('avg_stay', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='人均停留时长(分)')),
                ('live_duration', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='直播时长(分)')),
                ('live_cost', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='投流消耗(元)')),
                ('live_lead', models.IntegerField(default=0, verbose_name='留资数')),
                ('live_valid_lead', models.IntegerField(default=0, verbose_name='有效留资数')),
                ('lead_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='留资成本(元)')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='anchor_daily_reports', to=settings.AUTH_USER_MODEL, verbose_name='跟进人/录入人')),
            ],
            options={
                'verbose_name': '主播获客日报',
                'verbose_name_plural': '主播获客日报',
                'ordering': ['-date', 'channel_type'],
                'unique_together': {('channel_type', 'date', 'operator', 'anchor_name')},
            },
        ),
        migrations.CreateModel(
            name='LeadLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='已删除')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('channel', models.CharField(choices=[('PAID', '渠道获客-付费投放'), ('LIVE', '直播获客'), ('LOCAL_PUSH', '本地推投流获客'), ('AI', 'AI获客'), ('SOCIAL', '视频号/小红书/闲鱼获客'), ('OTHER', '其他')], db_index=True, default='LIVE', max_length=20, verbose_name='渠道')),
                ('date', models.DateField(db_index=True, verbose_name='日期')),
                ('customer_name', models.CharField(max_length=100, verbose_name='客户姓名')),
                ('contact', models.CharField(blank=True, max_length=100, verbose_name='客户联系方式')),
                ('need', models.TextField(blank=True, verbose_name='客户需求')),
                ('address', models.TextField(blank=True, verbose_name='客户地址')),
                ('is_passed', models.BooleanField(default=False, verbose_name='客户是否通过')),
                ('detail', models.TextField(blank=True, verbose_name='客户详情备注')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('follower', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='led_follow_leads', to=settings.AUTH_USER_MODEL, verbose_name='跟进人员')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lead_ledgers', to=settings.AUTH_USER_MODEL, verbose_name='录入人')),
            ],
            options={
                'verbose_name': '客户留资明细',
                'verbose_name_plural': '客户留资明细',
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AnchorAdStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='已删除')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('ad_type', models.CharField(choices=[('SHORT_VIDEO', '短视频图文投流'), ('LIVE_ROOM', '直播间投流')], db_index=True, default='SHORT_VIDEO', max_length=20, verbose_name='投流类型')),
                ('date', models.DateField(db_index=True, verbose_name='日期')),
                ('platform', models.CharField(blank=True, max_length=50, verbose_name='投放平台')),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='消耗金额(元)')),
                ('impression', models.IntegerField(default=0, verbose_name='展示次数')),
                ('click', models.IntegerField(default=0, verbose_name='点击次数')),
                ('private_msg', models.IntegerField(default=0, verbose_name='私信咨询数')),
                ('lead_count', models.IntegerField(default=0, verbose_name='线索留资数')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='anchor_ad_stats', to=settings.AUTH_USER_MODEL, verbose_name='录入人')),
            ],
            options={
                'verbose_name': '直播投流数据',
                'verbose_name_plural': '直播投流数据',
                'ordering': ['-date', 'ad_type'],
            },
        ),
    ]
