import type { Resource } from '../../lib/types'
import { crmResources } from './crm'
import { catalogResources } from './catalog'
import { inventoryResources } from './inventory'
import { purchasingResources } from './purchasing'
import { salesResources } from './sales'
import { financeResources } from './finance'
import { bankingResources } from './banking'
import { hrResources } from './hr'
import { automationResources } from './automation'
import { contractsResources } from './contracts'
import { deliveryResources } from './delivery'
import { fieldResources } from './field'
import { authOrgResources } from './auth_org'
import { filesResources } from './files'
import { integrationsResources } from './integrations'

// ترتیب منو/جدول‌ها همان ترتیب قبلی است؛ هر ماژول فایل خودش را دارد
const ORDER = ['customers', 'products', 'brands', 'categories', 'price-rules', 'warehouses', 'stock', 'transfers', 'stock-moves', 'stock-batches', 'stock-counts', 'suppliers', 'purchases', 'orders', 'invoices', 'payments', 'checks', 'bank-accounts', 'chequebooks', 'journal', 'accounts', 'fiscal', 'employees', 'attendance', 'leaves', 'shifts', 'payroll', 'leads', 'tasks', 'proposals', 'targets', 'contracts', 'deliveries', 'visits', 'visit-plans', 'geofences', 'geofence-events', 'users', 'roles', 'audit', 'documents', 'api-keys', 'webhooks']
const all: Resource[] = [
  ...crmResources,
  ...catalogResources,
  ...inventoryResources,
  ...purchasingResources,
  ...salesResources,
  ...financeResources,
  ...bankingResources,
  ...hrResources,
  ...automationResources,
  ...contractsResources,
  ...deliveryResources,
  ...fieldResources,
  ...authOrgResources,
  ...filesResources,
  ...integrationsResources,
]
const byP = Object.fromEntries(all.map(r => [r.path, r]))
export const resources: Resource[] = ORDER.map(p => byP[p])
export const byPath = Object.fromEntries(resources.map(r => [r.path, r]))
