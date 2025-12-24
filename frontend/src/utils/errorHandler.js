import { message, Modal } from 'antd';

/**
 * 错误类型枚举
 */
export const ErrorType = {
  NETWORK_ERROR: 'NETWORK_ERROR',      // 网络错误
  SERVER_ERROR: 'SERVER_ERROR',        // 服务端错误 (5xx)
  CLIENT_ERROR: 'CLIENT_ERROR',        // 客户端错误 (4xx)
  AUTH_ERROR: 'AUTH_ERROR',            // 认证错误
  VALIDATION_ERROR: 'VALIDATION_ERROR', // 验证错误
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'       // 未知错误
};

/**
 * 错误消息配置
 */
const errorMessages = {
  [ErrorType.NETWORK_ERROR]: {
    title: '网络连接错误',
    content: '无法连接到服务器，请检查网络连接后重试。',
    type: 'error'
  },
  [ErrorType.SERVER_ERROR]: {
    title: '服务器错误',
    content: '服务器暂时不可用，请稍后重试。',
    type: 'error'
  },
  [ErrorType.CLIENT_ERROR]: {
    title: '请求错误',
    content: '请求参数有误，请检查后重试。',
    type: 'warning'
  },
  [ErrorType.AUTH_ERROR]: {
    title: '认证失败',
    content: '登录已过期，请重新登录。',
    type: 'error'
  },
  [ErrorType.VALIDATION_ERROR]: {
    title: '验证错误',
    content: '输入数据格式不正确，请检查后重试。',
    type: 'warning'
  },
  [ErrorType.UNKNOWN_ERROR]: {
    title: '未知错误',
    content: '发生未知错误，请稍后重试或联系管理员。',
    type: 'error'
  }
};

/**
 * 判断错误类型
 */
function getErrorType(error) {
  if (!error) {
    return ErrorType.UNKNOWN_ERROR;
  }
  
  // 网络错误
  if (error.code === 'NETWORK_ERROR' || error.message?.includes('Network Error') || error.message?.includes('网络错误')) {
    return ErrorType.NETWORK_ERROR;
  }
  
  // 超时错误
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return ErrorType.NETWORK_ERROR;
  }
  
  // HTTP 状态码错误
  if (error.response) {
    const status = error.response.status;
    
    if (status >= 500) {
      return ErrorType.SERVER_ERROR;
    } else if (status === 401 || status === 403) {
      return ErrorType.AUTH_ERROR;
    } else if (status >= 400) {
      return ErrorType.CLIENT_ERROR;
    }
  }
  
  // 验证错误
  if (error.response?.data?.detail || error.response?.data?.errors) {
    return ErrorType.VALIDATION_ERROR;
  }
  
  return ErrorType.UNKNOWN_ERROR;
}

/**
 * 获取错误详情
 */
function getErrorDetails(error) {
  const errorType = getErrorType(error);
  const baseMessage = errorMessages[errorType];
  
  let details = baseMessage.content;
  
  // 如果有服务器返回的错误消息，使用它
  if (error.response?.data?.detail) {
    details = error.response.data.detail;
  } else if (error.response?.data?.message) {
    details = error.response.data.message;
  } else if (error.message) {
    details = error.message;
  }
  
  return {
    ...baseMessage,
    content: details,
    originalError: error
  };
}

/**
 * 显示错误弹窗
 */
export function showErrorModal(error, customOptions = {}) {
  const errorDetails = getErrorDetails(error);
  
  Modal[errorDetails.type]({
    title: errorDetails.title,
    content: errorDetails.content,
    okText: '确定',
    ...customOptions
  });
}

/**
 * 显示错误消息提示（轻量级）
 */
export function showErrorMessage(error, duration = 3) {
  const errorDetails = getErrorDetails(error);
  
  message[errorDetails.type]({
    content: `${errorDetails.title}: ${errorDetails.content}`,
    duration
  });
}

/**
 * 统一的错误处理函数
 */
export function handleApiError(error, options = {}) {
  const {
    showModal = false,      // 是否显示弹窗
    showMessage = true,     // 是否显示消息提示
    logError = true,        // 是否记录错误日志
    customMessage,          // 自定义消息
    onError                // 错误回调函数
  } = options;
  
  // 记录错误日志（开发环境）
  if (logError && import.meta.env?.DEV) {
    console.error('API Error:', error);
  }
  
  // 调用错误回调
  if (onError && typeof onError === 'function') {
    onError(error);
  }
  
  // 显示错误提示
  if (showModal) {
    showErrorModal(error, customMessage ? { content: customMessage } : {});
  } else if (showMessage) {
    showErrorMessage(error);
  }
  
  // 如果是认证错误，自动处理登出
  if (getErrorType(error) === ErrorType.AUTH_ERROR) {
    // 清除本地存储
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    
    // 刷新页面
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  }
  
  // 返回错误信息，方便进一步处理
  return getErrorDetails(error);
}

/**
 * 创建安全的API调用包装器
 */
export function createSafeApiCall(apiCall, options = {}) {
  return async (...args) => {
    try {
      const response = await apiCall(...args);
      return response;
    } catch (error) {
      if (error?.config?._skipAuthHandler === true) {
        throw error;
      }
      handleApiError(error, options);
      throw error; // 重新抛出错误，让调用方可以进一步处理
    }
  };
}

export default {
  ErrorType,
  showErrorModal,
  showErrorMessage,
  handleApiError,
  createSafeApiCall
};
