<template>
  <BaseListView
    :title="title"
    :baseUrl="baseUrl"
    :columns="columns"
    :formFields="resolvedFormFields"
    :searchFields="resolvedSearchFields"
    :readOnly="readOnly"
    :canDelete="canDelete"
    :rawArray="rawArray"
    :dialogWidth="dialogWidth"
  >
    <template #header-extra>
      <slot name="header-extra" />
    </template>
  </BaseListView>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'

const props = defineProps({
  title: { type: String, default: '' },
  baseUrl: { type: String, required: true },
  columns: { type: Array, default: () => [] },
  formFields: { type: Array, default: () => [] },
  searchFields: { type: Array, default: () => [] },
  // 外键下拉：{ field: 'user' -> '/accounts/users/' }
  depends: { type: Object, default: () => ({}) },
  readOnly: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: true },
  rawArray: { type: Boolean, default: false },
  dialogWidth: { type: String, default: '560px' },
})

const optionMap = ref({})

function pickLabel(it) {
  return it.display_name || it.name || it.username || it.title || ('#' + it.id)
}

async function loadDepends() {
  for (const field in props.depends) {
    try {
      const r = await http.get(props.depends[field], { params: { page_size: 500 } })
      const data = r?.results || (Array.isArray(r) ? r : (r?.data?.results || []))
      optionMap.value[field] = (data || []).map(it => ({ value: it.id, label: pickLabel(it) }))
    } catch (e) {
      optionMap.value[field] = []
    }
  }
}

const resolvedFormFields = computed(() =>
  props.formFields.map(f => {
    if (f.depends) {
      return { ...f, type: 'select', options: optionMap.value[f.depends] || [] }
    }
    return f
  })
)

const resolvedSearchFields = computed(() =>
  props.searchFields.map(f => {
    if (f.depends) {
      return { ...f, type: 'select', options: optionMap.value[f.depends] || [] }
    }
    return f
  })
)

onMounted(loadDepends)
</script>
