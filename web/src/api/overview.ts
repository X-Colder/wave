import client from './client'
import type { OverviewData } from '@/types'

export function fetchOverview() {
  return client.get<OverviewData>('/overview')
}
