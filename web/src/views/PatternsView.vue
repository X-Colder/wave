<script setup lang="ts">
import { onMounted } from 'vue'
import { usePatternsStore } from '@/stores/patterns'
import PatternHeatmap from '@/components/patterns/PatternHeatmap.vue'
import PatternDetail from '@/components/patterns/PatternDetail.vue'

const store = usePatternsStore()

onMounted(() => {
  store.load()
})

const accelerationLevels = [0, 1, 2]

function onCellClick(f: number, m: number, a: number, fd: number, md: number, ad: number) {
  store.loadDetail(f, m, a, fd, md, ad)
}
</script>

<template>
  <div class="patterns-view">
    <div v-if="store.loading" class="loading-overlay">
      <el-icon class="is-loading" size="32"><Loading /></el-icon>
      <span>加载模式数据...</span>
    </div>

    <template v-else-if="store.cells.length || !store.error">
      <div class="patterns-layout">
        <div class="heatmaps-panel">
          <div class="panel-title">模式热力图（加速度分面）</div>
          <div class="heatmaps-row">
            <PatternHeatmap
              v-for="level in accelerationLevels"
              :key="level"
              :cells="store.cells"
              :acceleration-level="level"
              @cell-click="onCellClick"
            />
          </div>
          <div class="heatmap-hint">点击单元格查看详情 &nbsp;·&nbsp; 颜色代表 MFE/MAE 比 &nbsp;·&nbsp; 透明度代表样本量</div>
        </div>

        <div class="detail-panel">
          <PatternDetail
            :detail="store.selectedDetail!"
            :loading="store.detailLoading"
          />
        </div>
      </div>
    </template>

    <div v-if="store.error && !store.loading" class="error-state">
      <el-icon size="40"><Warning /></el-icon>
      <p>{{ store.error }}</p>
      <el-button type="primary" @click="store.load()">重新加载</el-button>
    </div>
  </div>
</template>

<style scoped>
.patterns-view {
  height: 100%;
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

.patterns-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 120px);
}

.heatmaps-panel {
  flex: 7;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.panel-title {
  font-size: 14px;
  color: #a0cfff;
  font-weight: 500;
}

.heatmaps-row {
  display: flex;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.heatmap-hint {
  font-size: 11px;
  color: #8899aa;
  text-align: center;
}

.detail-panel {
  flex: 3;
  min-width: 260px;
  overflow: hidden;
}
</style>
