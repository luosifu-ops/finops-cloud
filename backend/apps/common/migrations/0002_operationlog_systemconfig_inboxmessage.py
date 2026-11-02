from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("user_name", models.CharField(blank=True, default="", max_length=50, verbose_name="操作人姓名")),
                ("action", models.CharField(choices=[("CREATE","新增"),("UPDATE","修改"),("DELETE","删除"),("BULK_DELETE","批量删除"),("IMPORT","导入"),("EXPORT","导出"),("APPROVE","审批通过"),("REJECT","审批驳回"),("ASSIGN","分配"),("RETURN","退回"),("LOGIN","登录"),("OTHER","其他")], default="OTHER", max_length=20, verbose_name="动作")),
                ("module", models.CharField(blank=True, default="", max_length=50, verbose_name="功能模块")),
                ("object_type", models.CharField(blank=True, default="", max_length=60, verbose_name="对象类型")),
                ("object_id", models.CharField(blank=True, default="", max_length=50, verbose_name="对象ID")),
                ("object_repr", models.CharField(blank=True, default="", max_length=200, verbose_name="对象摘要")),
                ("detail", models.TextField(blank=True, default="", verbose_name="变更明细")),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="op_logs", to="accounts.user", verbose_name="操作人")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "操作日志", "verbose_name_plural": "操作日志"},
        ),
        migrations.CreateModel(
            name="SystemConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("key", models.CharField(max_length=100, unique=True, verbose_name="配置键")),
                ("value", models.TextField(blank=True, default="", verbose_name="配置值")),
                ("remark", models.CharField(blank=True, default="", max_length=200, verbose_name="说明")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sys_configs_updated", to="accounts.user", verbose_name="最后修改人")),
            ],
            options={"ordering": ["key"], "verbose_name": "系统配置", "verbose_name_plural": "系统配置"},
        ),
        migrations.CreateModel(
            name="InboxMessage",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("title", models.CharField(max_length=200, verbose_name="标题")),
                ("body", models.TextField(blank=True, default="", verbose_name="内容")),
                ("category", models.CharField(blank=True, default="APPROVAL", max_length=30, verbose_name="类型")),
                ("link", models.CharField(blank=True, default="", max_length=200, verbose_name="跳转路径")),
                ("is_read", models.BooleanField(default=False, verbose_name="已读")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inbox_messages", to="accounts.user", verbose_name="接收人")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "站内消息", "verbose_name_plural": "站内消息"},
        ),
    ]
