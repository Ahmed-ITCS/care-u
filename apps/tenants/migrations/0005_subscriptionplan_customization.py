from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_subscription_plan_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='description',
            field=models.TextField(blank=True, help_text='Shown on the public pricing page'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, help_text='Lower numbers appear first on pricing'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='is_featured',
            field=models.BooleanField(default=False, help_text='Highlight as “Most popular” on pricing'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='trial_days',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Trial length when this plan is assigned (leave blank for non-trial plans)',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='support_level',
            field=models.CharField(
                choices=[
                    ('standard', 'Standard support'),
                    ('priority', 'Priority support'),
                    ('dedicated', 'Dedicated account manager'),
                ],
                default='standard',
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name='subscriptionplan',
            options={'ordering': ['sort_order', 'price_monthly']},
        ),
    ]
