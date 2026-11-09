<template>
  <el-menu
    :default-active="active"
    :collapse="collapsed"
    :collapse-transition="false"
    router
    class="side-menu"
  >
    <template v-for="grp in menuGroups" :key="grp.key">
      <!-- 无分组：直接作为顶级菜单项 -->
      <template v-if="!grp.name">
        <el-menu-item v-for="e in grp.entries" :key="e.item.path" :index="'/' + e.item.path">
          <el-icon><component :is="e.item.meta.icon" /></el-icon>
          <template #title><span>{{ e.item.meta.title }}</span></template>
        </el-menu-item>
      </template>

      <!-- 有分组：分组作为一级子菜单 -->
      <el-sub-menu v-else :index="grp.name">
        <template #title>
          <el-icon><component :is="groupIcon(grp)" /></el-icon>
          <span>{{ grp.name }}</span>
        </template>

        <!-- 分组内条目：按路由声明顺序混排（一级项 / 二级子菜单） -->
        <template v-for="(e, i) in grp.entries" :key="e.type + '-' + i">
          <el-menu-item v-if="e.type === 'root'" :index="'/' + e.item.path">
            <el-icon><component :is="e.item.meta.icon" /></el-icon>
            <template #title><span>{{ e.item.meta.title }}</span></template>
          </el-menu-item>

          <el-sub-menu v-else :index="grp.name + '/' + e.name">
            <template #title>
              <el-icon><component :is="parentIcon(e.name, e.items)" /></el-icon>
              <span>{{ e.name }}</span>
            </template>
            <el-menu-item v-for="item in e.items" :key="item.path" :index="'/' + item.path">
              <el-icon><component :is="item.meta.icon" /></el-icon>
              <template #title><span>{{ item.meta.title }}</span></template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { growthApi } from '@/api/growth'

defineProps({ collapsed: Boolean })
const router = useRouter()
const store = useUserStore()
const active = computed(() => router.currentRoute.value.path)

// 2026-11-03：closer_only 菜单（已承接线索池）仅成交师 / 管理层可见
const isCloserRole = ref(false)
onMounted(async () => {
  if (!store.token) return
  try {
    const r = await growthApi.myRole()
    isCloserRole.value = !!r && (!!r.can_view_all || (r.has_role && r.role === 'CLOSER') || !!r.can_assign_leads)
  } catch (e) { /* ignore */ }
})

const allRoutes = computed(() => {
  const root = router.options.routes.find(r => r.path === '/')
  // 必须带 meta 才进菜单：纯 redirect 路由（如 sales/data-wall）没有 meta，
  // 若进入菜单会在渲染 e.item.meta.title 时抛出 TypeError，导致整页空白。
  return (root?.children || []).filter(r => r.meta && !r.meta.hidden)
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

// 一级分组图标映射（未命中时回退到组内首个图标）
const groupIconMap = {
  '入职与成长': 'MagicStick',
  '增长中心': 'Promotion',
  '运营部': 'DataBoard',
  '电销部': 'Phone',
  '会计部': 'Coin',
  '外勤部': 'Van',
  '增值业务部': 'Goods',
  '行政人事部': 'UserFilled',
  '工作汇报': 'Notebook',
  '公司通知': 'Bell',
  '会员体系': 'Goods',
  '招商合作': 'Present',
  '系统管理': 'Setting',
}

/**
 * 菜单树构建
 * - 分组顺序 = 路由声明顺序（改顺序只需改 router/index.js）
 * - 组内条目按路由声明顺序「混排」：一级页与二级子菜单谁先声明谁在前，
 *   这样「入职资料 / 我的入职任务」可以自然插在「公司制度」与「专业基础知识」之间。
 * - 空组（无任何可见菜单项）不会进入结果：分组只在有路由通过权限校验时才创建，
 *   员工不会再看到「电销部」等无权限的空壳分组（2026-10-29 权限规则）。
 */
const menuGroups = computed(() => {
  const order = []                 // 分组出现顺序
  const map = new Map()            // name -> { key, name, entries, subIndex }

  for (const r of allRoutes.value) {
    const meta = r.meta || {}
    if (meta.admin && !store.isAdmin && !store.isHR) continue
    if (meta.leader && !store.isLeader) continue
    // manager_only: 仅 BOSS / MANAGER 可见（HR / LEADER / EMPLOYEE 均屏蔽）
    if (meta.manager_only && !store.isManager) continue
    // closer_only: 仅成交师 / 管理层可见（2026-11-03 已承接线索池）
    if (meta.closer_only && !isCloserRole.value) continue
    if (meta.dept) {
      const myDept = store.userInfo?.department_name || ''
      const dm = { SALES: '电销部', ACCOUNT: '会计部', OPS: '运营部' }
      const depts = Array.isArray(meta.dept) ? meta.dept : [meta.dept]
      const allowed = depts.map(d => dm[d]).filter(Boolean)
      if (!store.isBoss && !store.isHR && !allowed.includes(myDept)) continue
    }

    const g = meta.group || ''
    if (!map.has(g)) {
      const grp = { key: g || '_root', name: g, entries: [], subIndex: new Map() }
      map.set(g, grp)
      order.push(grp)
    }
    const grp = map.get(g)
    const parent = meta.parent || ''

    if (!parent) {
      grp.entries.push({ type: 'root', item: r })
      continue
    }
    // 二级子菜单：首次出现时插入一个 sub 条目，之后仅追加子项
    let idx = grp.subIndex.get(parent)
    if (idx === undefined) {
      grp.entries.push({ type: 'sub', name: parent, items: [r] })
      grp.subIndex.set(parent, grp.entries.length - 1)
    } else {
      grp.entries[idx].items.push(r)
    }
  }

  // 保证无分组项排在最前
  const rootGrp = order.find(g => !g.name)
  const rest = order.filter(g => g.name)
  return rootGrp ? [rootGrp, ...rest] : rest
})

function groupIcon(grp) {
  if (groupIconMap[grp.name]) return groupIconMap[grp.name]
  const first = grp.entries[0]
  if (!first) return 'Menu'
  return first.type === 'root' ? (first.item.meta.icon || 'Menu') : (first.items[0]?.meta?.icon || 'Menu')
}
function parentIcon(name, items) {
  if (parentIconMap[name]) return parentIconMap[name]
  return items[0]?.meta?.icon || 'Folder'
}
</script>

<style scoped>
.side-menu { border-right: none; background: transparent; }
</style>
