import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '../api/client'

export const useAdvisorStore = defineStore('advisor', () => {
  const advisors = ref([]) // 全部投顾列表
  const searchResults = ref([]) // 搜索结果
  const selectedPid = ref(null)
  const searchText = ref('')
  const showDropdown = ref(false)
  const hoverIdx = ref(-1)
  let searchTimer = null

  // 显示在下拉框的列表：无搜索时显示全部，有搜索时显示后端结果
  const displayAdvisors = computed(() => {
    return searchText.value ? searchResults.value : advisors.value
  })

  // 是否应该显示下拉框：仅在聚焦且有搜索词时显示
  const shouldShowDropdown = computed(() => {
    return showDropdown.value && searchText.value.trim().length > 0
  })

  async function fetchAdvisors() {
    try {
      const { data } = await client.get('/tables/advisor/performance/')
      advisors.value = data
      searchResults.value = data
      if (data.length && !selectedPid.value) {
        const found = data.find((a) => a.account_code === '250206_HC' || a.product_name === '250206_HC')
        const target = found || data[0]
        selectedPid.value = target.pid
        searchText.value = target.account_name || target.product_name
      }
    } catch (e) {
      console.error('获取投顾列表失败', e)
    }
  }

  // 后端模糊搜索（防抖 200ms）
  function onSearch() {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(async () => {
      const q = searchText.value.trim()
      try {
        const { data } = await client.get('/tables/advisor/performance/', {
          params: q ? { search: q } : {},
        })
        searchResults.value = data
      } catch (e) {
        console.error('搜索投顾失败', e)
      }
    }, 200)
  }

  function selectAdvisor(pid) {
    selectedPid.value = pid
    const list = searchResults.value.length ? searchResults.value : advisors.value
    const found = list.find((a) => a.pid === pid)
    if (found) searchText.value = found.account_name || found.product_name
    showDropdown.value = false
    hoverIdx.value = -1
  }

  function hoverNext() {
    if (hoverIdx.value < displayAdvisors.value.length - 1) hoverIdx.value++
  }
  function hoverPrev() {
    if (hoverIdx.value > 0) hoverIdx.value--
  }
  function confirmHover() {
    if (hoverIdx.value >= 0 && hoverIdx.value < displayAdvisors.value.length) {
      selectAdvisor(displayAdvisors.value[hoverIdx.value].pid)
    }
  }

  return {
    advisors,
    searchResults,
    displayAdvisors,
    shouldShowDropdown,
    selectedPid,
    searchText,
    showDropdown,
    hoverIdx,
    fetchAdvisors,
    onSearch,
    selectAdvisor,
    hoverNext,
    hoverPrev,
    confirmHover,
  }
})
