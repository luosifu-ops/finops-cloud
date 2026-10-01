from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0005_lead_contract_assigned_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='lead_no',
            field=models.CharField(blank=True, db_index=True, max_length=32, verbose_name='线索单号'),
        ),
    ]
