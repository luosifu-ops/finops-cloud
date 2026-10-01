<template>
  <el-menu
    :default-active="active"
    :collapse="collapsed"
    :collapse-transition="false"
    router
  >
    <template v-for="(group, gname) in menuGroups" :key="gname">
      <!-- 无分组：直接作为顶级菜单项 -->
      <template v-if="!gname">
        <el-menu-item v-for="item in group.roots" :key="item.path" :index="'/' + item.path">
          <el-icon><component :is="item.meta.icon" /></el-icon>
          <span>{{ item.meta.title }}</span>
        </el-menu-item>
      </template>

      <!-- 有分组：分组作为一级子菜单 -->
      <el-sub-menu v-else :index="gname">
        <template #title>
          <el-icon><component :is="groupIcon(group)" /></el-icon>
          <span>{{ gname }}</span>
        </template>

        <!-- 分组下的直接菜单项 -->
        <el-menu-item v-for="item in group.roots" :key="item.path" :index="'/' + item.path">
          <el-icon><component :is="item.meta.icon" /></el-icon>
          <span>{{ item.meta.title }}</span>
        </el-menu-item>

        <!-- 分组下的二级子菜单（父级） -->
        <el-sub-menu v-for="(subs, sname) in group.subs" :key="sname" :index="gname + '/' + sname">
          <template #title>
            <el-icon><component :is="parentIcon(group, sname, subs)" /></el-icon>
            <span>{{ sname }}</span>
          </template>
          <el-menu-item v-for="item in subs" :key="item.path" :index="'/' + item.path">
            <el-icon><component :is="item.meta.icon" /></el-icon>
            <span>{{ item.meta.title }}</span>
          </el-menu-item>
        </el-sub-menu>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const props = defineProps({ collapsed: Boolean })
const router = useRouter()
const store = useUserStore()
const active = computed(() => router.currentRoute.value.path)

const allRoutes = computed(() => {
  const root = router.options.routes.find(r => r.path === '/')
  return (root?.children || []).filter(r => !r.meta?.hidden)
})

// 二级父菜单图标映射
const parentIconMap = {
  '企业文化': 'OfficeBuilding',
  '公司制度': 'Document',
  '专业基础知识': 'Reading',
  '组织与人员': 'OfficeBuilding',
  '入转调离': 'Switch',
  '考勤与审批': 'Clock',
  '薪酬绩效': 'Money',
  '外勤': 'Van',
  '增值业务': 'Goods',
  '合同订单名录': 'Document',
}

const menuGroups = computed(() => {
  const groups = {}
  for (const r of allRoutes.value) {
    const meta = r.meta || {}
    if (meta.admin && !store.isAdmin && !store.isHR) continue
    if (meta.leader && !store.isLeader) continue
    // manager_only: 仅 BOSS / MANAGER 可见（HR / LEADER / EMPLOYEE 均屏蔽）
    // 用于 Boss 2026-09-07 指示"只有管理层和老板才可以看到所有数据"
    if (meta.manager_only && !store.isManager) continue
    if (meta.dept) {
      const myDept = store.userInfo?.department_name || ''
      const map = { SALES: '电销部', ACCOUNT: '会计部', OPS: '运营部' }
      // 支持单部门字符串或多部门数组（如 dept: ['SALES','OPS']）
      const depts = Array.isArray(meta.dept) ? meta.dept : [meta.dept]
      const allowed = depts.map(d => map[d]).filter(Boolean)
      if (!store.isBoss && !store.isHR && !allowed.includes(myDept)) continue
    }
    const g = meta.group || ''
    if (!groups[g]) groups[g] = { roots: [], subs: {} }
    const parent = meta.parent || ''
    if (parent) {
      if (!groups[g].subs[parent]) groups[g].subs[parent] = []
      groups[g].subs[parent].push(r)
    } else {
      groups[g].roots.push(r)
    }
  }
  // 保证无分组项排在最前
  const ordered = {}
  if (groups['']) { ordered[''] = groups['']; delete groups[''] }
  Object.assign(ordered, groups)
  return ordered
})

function groupIcon(group) {
  return group.roots[0]?.meta?.icon || 'Menu'
}
function parentIcon(group, sname, subs) {
  if (parentIconMap[sname]) return parentIconMap[sname]
  return subs[0]?.meta?.icon || 'Folder'
}
</script>
