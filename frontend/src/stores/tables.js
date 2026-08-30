import { defineStore } from 'pinia'
import client from '../api/client'

export const useTablesStore = defineStore('tables', {
  state: () => ({
    existingTables: [],
    dynamicTables: [],
    loading: false,
  }),
  getters: {
    all: (state) => [
      ...state.existingTables.map((t) => ({ ...t, kind: 'existing' })),
      ...state.dynamicTables.map((t) => ({ ...t, kind: 'dynamic' })),
    ],
    momTables: (state) => state.existingTables.filter((t) => ['mom', 'performance', 'rh'].includes(t.group)),
    performanceTables: (state) => state.existingTables.filter((t) => t.group === 'performance'),
    rhTables: (state) => state.existingTables.filter((t) => t.group === 'rh'),
    quoteTables: (state) => state.existingTables.filter((t) => t.group === 'quotes'),
    futuresTables: (state) => state.existingTables.filter((t) => t.group === 'futures'),
    optionsTables: (state) => state.existingTables.filter((t) => t.group === 'options'),
    fofTables: (state) => state.existingTables.filter((t) => t.group === 'fof'),
  },
  actions: {
    async fetchExisting() {
      const { data } = await client.get('/tables/')
      this.existingTables = data
    },
    async fetchDynamic() {
      const { data } = await client.get('/dynamic/')
      this.dynamicTables = data
    },
    async fetchAll() {
      this.loading = true
      try {
        await Promise.all([this.fetchExisting(), this.fetchDynamic()])
      } finally {
        this.loading = false
      }
    },
  },
})
