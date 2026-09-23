import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 前台分析页公开访问，401 不强制跳转；仅后台管理需要登录
      const path = window.location.pathname
      if (path.startsWith('/admin')) {
        window.location.href = '/login?redirect=' + encodeURIComponent(path)
      }
    }
    return Promise.reject(error)
  }
)

export default client
