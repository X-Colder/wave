import axios from 'axios'
import { ElMessage } from 'element-plus'

const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message =
      error.response?.data?.message ||
      error.message ||
      '请求失败，请检查网络连接'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default client
