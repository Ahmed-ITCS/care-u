from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_subscription_plan_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='hospital',
            name='stripe_customer_id',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='hospital',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='stripe_price_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='stripe_product_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='StripeWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_event_id', models.CharField(max_length=255, unique=True)),
                ('event_type', models.CharField(max_length=128)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-processed_at'],
            },
        ),
    ]
