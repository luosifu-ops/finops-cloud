from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="channelbudget",
            name="approve_status",
            field=models.CharField(choices=[("APPROVED", "已生效"), ("PENDING", "待审批"), ("REJECTED", "已驳回")], db_index=True, default="APPROVED", max_length=20, verbose_name="审批状态"),
        ),
        migrations.AddField(
            model_name="channelbudget",
            name="pending_budget",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="待审批预算"),
        ),
        migrations.AddField(
            model_name="channelbudget",
            name="pending_reason",
            field=models.CharField(blank=True, max_length=300, verbose_name="申请理由"),
        ),
        migrations.AddField(
            model_name="channelbudget",
            name="reviewer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_budgets", to="accounts.user", verbose_name="审批人"),
        ),
        migrations.AddField(
            model_name="channelbudget",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="审批时间"),
        ),
        migrations.AddField(
            model_name="channelbudget",
            name="reject_reason",
            field=models.CharField(blank=True, max_length=300, verbose_name="驳回理由"),
        ),
    ]
