"""Facade: schemaها در schemas.py هر ماژول تعریف می‌شوند؛ این فایل برای سازگاری importهای قدیمی همه را یکجا برمی‌گرداند."""
from app.core.schema_utils import _rt  # noqa: F401
from app.modules.auth_org.schemas import LoginIn,PasswordChangeIn,OrgIn,BranchIn,UserIn,RoleIn,MembershipIn,UserPatch,PasswordResetIn
from app.modules.finance.schemas import FiscalPeriodIn,PaymentIn,CheckIn,CheckStatusIn,CheckEndorseIn,JLineIn,JournalIn,AccountIn,AccountPatch
from app.modules.hr.schemas import LeaveIn,PayrollRunIn,EmployeeIn
from app.modules.crm.schemas import CustomerIn
from app.modules.catalog.schemas import ProductIn,ProductPatch,BrandIn,CategoryIn,PriceRuleIn,UnitIn,CampaignIn
from app.modules.inventory.schemas import WarehouseIn,StockIn,TransferIn,TransferItemIn,LocationIn,CountIn,CountLineIn,CountLinesIn,CountApproveIn
from app.modules.sales.schemas import ItemIn,OrderIn,InvoiceNoteIn,InvoiceTermsIn,ReturnItemIn,ReturnIn
from app.modules.field.schemas import VisitIn,PlanIn,VisitFinishIn,VisitRadiusIn
from app.modules.delivery.schemas import DeliveryIn,DeliveredItem,DeliveryUpdate,CollectIn,BulkAssignIn
from app.modules.purchasing.schemas import PurchaseItemIn,PurchaseIn,PurchaseReturnItem,PurchaseReturnIn,PurchaseReceiptItem,PurchaseReceiptIn,CostAllocationIn
from app.modules.banking.schemas import BankAccountIn,BankAccountPatch,ChequebookIn,ChequebookPatch,LeafVoidIn,BankTransferIn
from app.modules.automation.schemas import LeadIn,LeadStageIn,LeadActivityIn,TaskIn,TaskPatch,ProposalItemIn,ProposalIn,ProposalAcceptIn,TargetIn
from app.modules.platform.schemas import BrandingIn,TaxIn
from app.modules.gps.schemas import GpsPointIn,GpsBatchIn,TrackingSettingsIn

from app.modules.banking.schemas import BankChargeIn, ReconcileIn

from app.modules.finance.schemas import JournalTemplateIn, TemplatePostIn
