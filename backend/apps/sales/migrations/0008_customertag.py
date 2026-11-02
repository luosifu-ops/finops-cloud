from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0007_alter_contract_contract_no_alter_lead_lead_no"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerTag",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="已删除")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="删除时间")),
                ("name", models.CharField(max_length=30, unique=True, verbose_name="标签名称")),
                ("color", models.CharField(default="primary", help_text="前端标签配色：primary/success/warning/danger/info", max_length=20, verbose_name="标签颜色")),
                ("sort", models.IntegerField(default=0, verbose_name="排序")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
                ("remark", models.CharField(blank=True, max_length=200, verbose_name="说明")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="accounts.user", verbose_name="创建人")),
            ],
            options={"verbose_name": "客户标签", "verbose_name_plural": "客户标签", "ordering": ["sort", "id"]},
        ),
        migrations.AddField(
            model_name="customer",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="customers", to="sales.customertag", verbose_name="客户标签"),
        ),
    ]
