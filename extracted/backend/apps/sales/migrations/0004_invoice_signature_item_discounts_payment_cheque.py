from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('sales', '0003_invoice_payment_status')]
    operations = [
        migrations.AddField(model_name='invoice', name='customer_signature', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='invoice', name='customer_signature_name', field=models.CharField(blank=True, default='', max_length=200)),
        migrations.AddField(model_name='invoice', name='customer_signed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='invoiceitem', name='company_discount_percent', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AddField(model_name='invoiceitem', name='offer_percent', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AddField(model_name='payment', name='cheque_number', field=models.CharField(blank=True, default='', max_length=64)),
        migrations.AddField(model_name='payment', name='cheque_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='payment', name='cheque_bank', field=models.CharField(blank=True, default='', max_length=100)),
    ]
