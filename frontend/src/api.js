import axios from 'axios';
import { handleApiError, createSafeApiCall } from './utils/errorHandler';

// 创建axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
});

// 请求拦截器：添加认证令牌
api.interceptors.request.use(
  (config) => {
    // 从localStorage获取令牌
    const token = localStorage.getItem('token');
    if (token) {
      // 添加Authorization头
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // 处理请求错误
    return Promise.reject(error);
  }
);

// 响应拦截器：处理令牌过期或无效
api.interceptors.response.use(
  (response) => {
    // 2xx范围内的状态码都会触发该函数
    return response;
  },
  (error) => {
    // 非2xx范围内的状态码都会触发该函数
    if (error.response) {
      // 服务器返回了错误响应
      if (error.response.status === 401) {
        // 令牌过期或无效，清除本地存储并跳转到登录页面
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        // 显示认证错误提示
        handleApiError(error, { showModal: true });
      }
    }
    return Promise.reject(error);
  }
);

// 创建安全的API调用包装器
const safeApiCall = createSafeApiCall;

// 安全的API方法
export const safeApi = {
  get: (url, config) => safeApiCall(api.get, { showMessage: true })(url, config),
  post: (url, data, config) => safeApiCall(api.post, { showMessage: true })(url, data, config),
  put: (url, data, config) => safeApiCall(api.put, { showMessage: true })(url, data, config),
  delete: (url, config) => safeApiCall(api.delete, { showMessage: true })(url, config),
  patch: (url, data, config) => safeApiCall(api.patch, { showMessage: true })(url, data, config)
};

// 暂停生成接口
export const stopGeneration = async (sessionId) => {
  return safeApiCall(api.post, { 
    showMessage: true,
    customMessage: '暂停生成失败，请稍后重试'
  })(`/sessions/${sessionId}/stop`);
};

// 导出原始API（用于需要自定义错误处理的场景）
export { api as rawApi };

export default safeApi;
