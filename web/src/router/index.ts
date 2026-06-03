import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'overview',
          component: () => import('@/views/OverviewView.vue'),
        },
        {
          path: 'patterns',
          name: 'patterns',
          component: () => import('@/views/PatternsView.vue'),
        },
        {
          path: 'trades',
          name: 'trades',
          component: () => import('@/views/TradesView.vue'),
        },
        {
          path: 'intraday',
          name: 'intraday',
          component: () => import('@/views/IntradayView.vue'),
        },
      ],
    },
  ],
})

export default router
