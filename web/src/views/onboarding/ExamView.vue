<template>
  <div class="exam-mod">
    <el-tabs v-model="tab" class="exam-tabs">
      <el-tab-pane label="考试中心" name="center" />
      <el-tab-pane label="题库管理" name="bank" />
      <el-tab-pane label="错题本" name="wrong" />
      <el-tab-pane label="考试记录" name="records" />
    </el-tabs>
    <component :is="current" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ExamCenterView from './exam/ExamCenterView.vue'
import BankView from './exam/BankView.vue'
import WrongBookView from './exam/WrongBookView.vue'
import RecordsView from './exam/RecordsView.vue'

const tab = ref('center')
const map = { center: ExamCenterView, bank: BankView, wrong: WrongBookView, records: RecordsView }
const current = computed(() => map[tab.value])
</script>

<style scoped>
.exam-mod { padding: 4px; }
.exam-tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
</style>
