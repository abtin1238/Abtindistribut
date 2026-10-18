import type { Resource } from '../../lib/types'
import { st, c, ref } from './helpers'

export const deliveryResources: Resource[] = [
  { path: 'deliveries', title: 'پخش و تحویل', endpoint: '/deliveries', columns: [c('order_id', 'سفارش'), ref('driver_id', 'مأمور', '/users'), st(), c('reason', 'دلیل'), c('delivered_at', 'زمان تحویل', 'date'), c('gps_status', 'GPS')] },
]
