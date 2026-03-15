from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="tiebreak_order",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
