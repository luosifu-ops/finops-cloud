from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('growth', '0007_fieldtask_assignee_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='fieldtask',
            name='task_no',
            field=models.CharField(blank=True, db_index=True, max_length=32, verbose_name='派单号'),
        ),
    ]
