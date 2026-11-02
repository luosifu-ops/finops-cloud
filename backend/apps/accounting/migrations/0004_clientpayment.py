from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0003_bookset"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientPayment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="已删除")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="删除时间")),
                ("period", models.CharField(db_index=True, help_text="如 2026-10、2026-Q4、2026-年度", max_length=20, verbose_name="服务期间")),
                ("amount_due", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="应收金额(元)")),
                ("amount_paid", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="已收金额(元)")),
                ("paid_date", models.DateField(blank=True, null=True, verbose_name="收款日期")),
                ("method", models.CharField(blank=True, choices=[("BANK", "对公转账"), ("WX", "微信"), ("ALIPAY", "支付宝"), ("CASH", "现金"), ("OTHER", "其他")], default="BANK", max_length=20, verbose_name="收款方式")),
                ("status", models.CharField(choices=[("UNPAID", "未收"), ("PARTIAL", "部分到账"), ("PAID", "已收清"), ("REFUNDED", "已退费")], db_index=True, default="UNPAID", max_length=20, verbose_name="状态")),
                ("voucher_no", models.CharField(blank=True, max_length=60, verbose_name="收据/流水号")),
                ("remark", models.CharField(blank=True, max_length=300, verbose_name="备注")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="accounting.accountingclient", verbose_name="代账客户")),
                ("operator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="client_payments", to="accounts.user", verbose_name="经手人")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="accounts.user", verbose_name="创建人")),
            ],
            options={"verbose_name": "服务费收款", "verbose_name_plural": "服务费收款", "ordering": ["-period", "-created_at"]},
        ),
    ]
