/**
 * 错误处理系统使用示例
 * 
 * 这个文件展示了如何在你的React组件中使用新的错误处理系统
 */

import { handleApiError, showErrorModal, showErrorMessage, createSafeApiCall } from './errorHandler';
import api from '../api';

// 示例1: 基本的API调用错误处理
async function exampleBasicApiCall() {
  try {
    const response = await api.get('/some-endpoint');
    return response.data;
  } catch (error) {
    // 使用统一的错误处理函数
    handleApiError(error, {
      showMessage: true,      // 显示消息提示
      customMessage: '获取数据失败' // 自定义错误消息
    });
    throw error; // 重新抛出错误，让调用方可以进一步处理
  }
}

// 示例2: 显示错误弹窗
async function exampleShowModal() {
  try {
    const response = await api.post('/some-endpoint', { data: 'test' });
    return response.data;
  } catch (error) {
    // 显示错误弹窗而不是消息提示
    handleApiError(error, {
      showModal: true,        // 显示弹窗
      showMessage: false,     // 不显示消息提示
      customMessage: '操作失败，请检查输入数据'
    });
    throw error;
  }
}

// 示例3: 自定义错误回调
async function exampleWithCallback() {
  try {
    const response = await api.put('/some-endpoint', { data: 'update' });
    return response.data;
  } catch (error) {
    handleApiError(error, {
      showMessage: true,
      onError: (error) => {
        // 自定义错误处理逻辑
        console.log('自定义错误处理:', error);
        // 可以在这里执行其他操作，比如记录日志、发送错误报告等
      }
    });
    throw error;
  }
}

// 示例4: 创建安全的API调用包装器
const safeApiCall = createSafeApiCall(api.get, {
  showMessage: true,
  customMessage: '获取用户信息失败'
});

// 使用安全的API调用
async function exampleSafeApiCall() {
  try {
    // 这个调用会自动处理错误
    const response = await safeApiCall('/users/1');
    return response.data;
  } catch (error) {
    // 错误已经被处理，这里可以执行其他逻辑
    console.log('API调用失败，但错误已经被处理');
    throw error;
  }
}

// 示例5: 直接使用错误处理函数
function exampleDirectErrorHandling() {
  // 显示错误消息提示
  showErrorMessage(new Error('这是一个测试错误'));
  
  // 显示错误弹窗
  showErrorModal(new Error('这是一个严重的错误'));
}

// 示例6: 在React组件中使用
function ExampleComponent() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/data');
      setData(response.data);
    } catch (error) {
      handleApiError(error, {
        showMessage: true,
        customMessage: '加载数据失败'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (formData) => {
    try {
      const response = await api.post('/api/submit', formData);
      message.success('提交成功！');
      return response.data;
    } catch (error) {
      handleApiError(error, {
        showModal: true, // 对于重要操作，使用弹窗
        customMessage: '提交失败，请检查数据后重试'
      });
      throw error;
    }
  };

  return (
    <div>
      <button onClick={fetchData} disabled={loading}>
        {loading ? '加载中...' : '获取数据'}
      </button>
      {/* 组件内容 */}
    </div>
  );
}

// 示例7: 处理不同类型的错误
export const ErrorType = {
  NETWORK_ERROR: 'NETWORK_ERROR',      // 网络错误
  SERVER_ERROR: 'SERVER_ERROR',        // 服务端错误 (5xx)
  CLIENT_ERROR: 'CLIENT_ERROR',        // 客户端错误 (4xx)
  AUTH_ERROR: 'AUTH_ERROR',            // 认证错误
  VALIDATION_ERROR: 'VALIDATION_ERROR', // 验证错误
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'       // 未知错误
};

// 错误处理系统会自动识别错误类型并显示相应的消息

/**
 * 最佳实践建议:
 * 
 * 1. 对于重要的用户操作（如提交表单、删除数据），使用 showModal: true 显示弹窗
 * 2. 对于一般的API调用错误，使用 showMessage: true 显示消息提示
 * 3. 在开发环境中，保持 logError: true 以便调试
 * 4. 使用 customMessage 提供更友好的错误描述
 * 5. 对于需要特殊处理的错误，使用 onError 回调
 * 6. 对于频繁调用的API，使用 createSafeApiCall 创建安全的包装器
 */