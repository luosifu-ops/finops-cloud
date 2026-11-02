from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_alter_department_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="entryapplication",
            name="password_hash",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="登录密码(哈希)"),
        ),
    ]
