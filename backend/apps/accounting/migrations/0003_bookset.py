from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookSet",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="已删除")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="删除时间")),
                ("name", models.CharField(max_length=200, verbose_name="账套名称")),
                ("taxpayer_type", models.CharField(choices=[("GENERAL", "一般纳税人"), ("SMALL", "小规模纳税人"), ("INDIVIDUAL", "个体工商户")], default="SMALL", max_length=20, verbose_name="纳税人类型")),
                ("period", models.CharField(db_index=True, help_text="如 2026-10", max_length=7, verbose_name="当前会计期间")),
                ("opening_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="期初余额(元)")),
                ("voucher_count", models.IntegerField(default=0, verbose_name="凭证数")),
                ("yz_account_no", models.CharField(blank=True, db_index=True, max_length=60, verbose_name="云账房账套号")),
                ("status", models.CharField(choices=[("ACTIVE", "启用中"), ("PAUSED", "已暂停"), ("CLOSED", "已封存")], default="ACTIVE", max_length=20, verbose_name="状态")),
                ("remark", models.CharField(blank=True, max_length=300, verbose_name="备注")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="book_sets", to="accounting.accountingclient", verbose_name="代账客户")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="accounts.user", verbose_name="创建人")),
            ],
            options={"verbose_name": "账套", "verbose_name_plural": "账套", "ordering": ["-created_at"]},
        ),
    ]
