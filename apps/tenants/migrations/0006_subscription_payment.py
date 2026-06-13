from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0005_stripe_billing'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('stripe', 'Stripe (Card)'), ('jazzcash', 'JazzCash'), ('easypaisa', 'Easypaisa')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='PKR', max_length=3)),
                ('txn_ref', models.CharField(db_index=True, max_length=64, unique=True)),
                ('gateway_txn_id', models.CharField(blank=True, max_length=128)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], db_index=True, default='pending', max_length=20)),
                ('gateway_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('hospital', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_payments', to='tenants.hospital')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='tenants.subscriptionplan')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
