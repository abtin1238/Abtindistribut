from rest_framework import serializers
from .models import Customer, PriceLevel, ProductPrice, Campaign, Invoice, InvoiceItem, InvoiceStatusHistory, ApprovalRequest, Payment

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class PriceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceLevel
        fields = '__all__'

class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    method_label = serializers.CharField(source='get_method_display', read_only=True)
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('received_by', 'received_at')

class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = InvoiceItem
        fields = ('id', 'product', 'product_name', 'warehouse', 'qty', 'unit_price', 'discount_percent', 'company_discount_percent', 'offer_percent', 'discount_amount', 'tax_amount', 'line_total')
        read_only_fields = ('warehouse', 'discount_percent', 'discount_amount', 'tax_amount', 'line_total')
        extra_kwargs = {'unit_price': {'required': False, 'allow_null': True}}

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    payments = PaymentSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=16, decimal_places=0, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_label = serializers.CharField(source='get_payment_status_display', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    branch_name = serializers.CharField(source='warehouse.branch.name', read_only=True)
    company_name = serializers.CharField(source='warehouse.branch.company.name', read_only=True)
    company_phone = serializers.CharField(source='warehouse.branch.company.phone', read_only=True)
    company_address = serializers.CharField(source='warehouse.branch.company.address', read_only=True)
    company_economic_code = serializers.CharField(source='warehouse.branch.company.economic_code', read_only=True)
    seller_name = serializers.SerializerMethodField()
    class Meta:
        model = Invoice
        fields = ('id', 'number', 'customer', 'customer_name', 'warehouse', 'warehouse_name', 'branch_name', 'company_name', 'company_phone', 'company_address', 'company_economic_code', 'seller', 'seller_name', 'status', 'status_label', 'items', 'payments', 'status_history', 'customer_name_snapshot', 'customer_address_snapshot', 'customer_latitude_snapshot', 'customer_longitude_snapshot', 'customer_signature', 'customer_signature_name', 'customer_signed_at', 'subtotal', 'discount_total', 'tax_total', 'total', 'paid_total', 'balance', 'payment_status', 'payment_status_label', 'credit_approval_required', 'created_at', 'updated_at')
        read_only_fields = ('seller', 'status', 'payment_status', 'customer_name_snapshot', 'customer_address_snapshot', 'customer_latitude_snapshot', 'customer_longitude_snapshot', 'subtotal', 'discount_total', 'tax_total', 'total', 'paid_total', 'credit_approval_required', 'payments', 'status_history', 'customer_signed_at')

    def get_seller_name(self, obj):
        return obj.seller.get_full_name() or obj.seller.username

    def get_status_history(self, obj):
        return [{
            'id': h.id, 'from_status': h.from_status, 'to_status': h.to_status,
            'to_status_label': h.get_to_status_display(), 'note': h.note,
            'changed_by': h.changed_by.get_full_name() or h.changed_by.username,
            'created_at': h.created_at,
        } for h in obj.status_history.all()]

class InvoiceStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceStatusHistory
        fields = '__all__'

class ApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequest
        fields = '__all__'
        read_only_fields = ('status', 'decided_by', 'decided_at')

class InvoiceActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')

class PaymentActionSerializer(serializers.Serializer):
    invoice = serializers.IntegerField()
    method = serializers.ChoiceField(choices=Payment.METHODS)
    amount = serializers.DecimalField(max_digits=16, decimal_places=0, min_value=1)
    reference = serializers.CharField(required=False, allow_blank=True, default='')
    cheque_number = serializers.CharField(required=False, allow_blank=True, default='')
    cheque_date = serializers.DateField(required=False, allow_null=True)
    cheque_bank = serializers.CharField(required=False, allow_blank=True, default='')

class InvoiceSignatureSerializer(serializers.Serializer):
    signature = serializers.CharField(min_length=20)
    signer_name = serializers.CharField(max_length=200)
