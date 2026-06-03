<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useOverviewStore } from '@/stores/overview'
import MetricsCard from '@/components/overview/MetricsCard.vue'
import EquityCurve from '@/components/overview/EquityCurve.vue'
import DrawdownChart from '@/components/overview/DrawdownChart.vue'
import MonthlyReturns from '@/components/overview/MonthlyReturns.vue'

const store = useOverviewStore()

onMounted(() => {
  store.load()
})

function pct(val: number) {
  return `${(val * 100).toFixed(2)}%`
}

function toFixed2(val: number) {
  return val.toFixed(2)
}

const kpiCards = computed(() => {
  const m = store.data?.metrics
  if (!m) return []
  return [
    {
      title: '年化收益率',
      value: pct(m.annual_return),
      valueClass: m.annual_return >= 0 ? 'text-profit' : 'text-loss',
      subtext: `总收益: ${pct(m.total_return)}`,
    },
    {
      title: '最大回撤',
      value: pct(m.max_drawdown),
      valueClass: 'text-loss',
    },
    {
      title: '夏普比率',
      value: toFixed2(m.sharpe_ratio),
      valueClass: m.sharpe_ratio >= 1 ? 'text-profit' : 'text-neutral',
    },
    {
      title: '减仓胜率',
      value: pct(m.win_rate),
      valueClass: m.win_rate >= 0.5 ? 'text-profit' : 'text-loss',
    },
    {
      title: '盈亏比',
      value: toFixed2(m.profit_loss_ratio),
      valueClass: m.profit_loss_ratio >= 1 ? 'text-profit' : 'text-loss',
    },
    {
      title: '平均仓位',
      value: pct(m.avg_position ?? 0),
      valueClass: 'text-neutral',
      subtext: `加${m.buy_adjustments ?? 0} 减${m.sell_adjustments ?? 0}`,
    },
  ]
})
</script>

<template>
  <div class="overview-view">
    <div v-if="store.loading" class="loading-overlay">
      <el-icon class="is-loading" size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <template v-else-if="store.data">
      <div class="kpi-grid">
        <MetricsCard
          v-for="card in kpiCards"
          :key="card.title"
          :title="card.title"
          :value="card.value"
          :subtext="card.subtext"
          :value-class="card.valueClass"
        />
      </div>

      <div class="equity-section">
        <EquityCurve :data="store.data.equity_curve" />
      </div>

      <div class="bottom-section">
        <div class="bottom-left">
          <DrawdownChart :data="store.data.equity_curve" />
        </div>
        <div class="bottom-right">
          <MonthlyReturns :data="store.data.monthly_returns" />
        </div>
      </div>
    </template>

    <div v-else-if="store.error" class="error-state">
      <el-icon size="40"><Warning /></el-icon>
      <p>{{ store.error }}</p>
      <el-button type="primary" @click="store.load()">重新加载</el-button>
    </div>
  </div>
</template>

<style scoped>
.overview-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 400px;
  color: #8899aa;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  height: 400px;
  color: #f56c6c;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}

.equity-section {
  width: 100%;
}

.bottom-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.bottom-left,
.bottom-right {
  min-width: 0;
}

@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .bottom-section {
    grid-template-columns: 1fr;
  }
}
</style>
