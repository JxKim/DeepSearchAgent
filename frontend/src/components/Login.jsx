import { useState } from 'react';
import api from '../api';
import { Modal, Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined, CloseOutlined } from '@ant-design/icons';
import './Login.css';

const Login = ({ onLogin, onClose }) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values) => {
    setLoading(true);

    try {
      let response;
      if (isRegistering) {
        // 调用注册API
        response = await api.post('/auth/register', {
          username: values.username,
          password: values.password,
          email: `${values.username}@example.com`,
          full_name: values.username
        });
        message.success('注册成功！');
      } else {
        // 调用登录API
        response = await api.post('/auth/login', {
          username: values.username,
          password: values.password
        }, { 
          // 告诉拦截器跳过全局的认证错误处理，防止自动刷新
          _skipAuthHandler: true 
        });
        message.success('登录成功！');
      }
      
      // 处理API响应
      const token = response.data.access_token;
      
      // 调用验证令牌API获取用户信息
      // 显式传递token参数和Authorization头，确保后端能正确识别
      const meResponse = await api.get('/auth/me', { 
        params: { token },
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      // 构建用户数据
      const userData = {
        id: meResponse.data.id,
        username: meResponse.data.username,
        email: meResponse.data.email,
        full_name: meResponse.data.full_name,
        token: token
      };
      
      // 存储用户数据和令牌到localStorage
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('token', token);
      
      // 调用父组件的登录回调
      onLogin(userData);
      onClose();
    } catch (err) {
      console.error('Login failed:', err);
      // 完全接管错误处理，不调用 handleApiError 以防止触发全局的刷新逻辑
      if (err.response) {
        if (err.response.status === 401 || err.response.status === 403) {
          message.error('登录失败：用户名或密码错误');
        } else if (err.response.data && err.response.data.detail) {
          message.error(`登录失败：${err.response.data.detail}`);
        } else {
          message.error('登录失败，请稍后重试');
        }
      } else if (err.request) {
        message.error('网络错误，无法连接到服务器');
      } else {
        message.error('发生未知错误');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={isRegistering ? '用户注册' : '用户登录'}
      open={true}
      onCancel={onClose}
      footer={null}
      width={400}
      closeIcon={<CloseOutlined />}
      centered
    >
      <Form
        name="login-form"
        onFinish={handleSubmit}
        autoComplete="off"
        layout="vertical"
      >
        <Form.Item
          label="用户名"
          name="username"
          rules={[
            { required: true, message: '请输入用户名!' },
            { min: 3, message: '用户名至少3个字符!' }
          ]}
        >
          <Input 
            prefix={<UserOutlined />} 
            placeholder="请输入用户名"
            size="large"
          />
        </Form.Item>

        <Form.Item
          label="密码"
          name="password"
          rules={[
            { required: true, message: '请输入密码!' },
            { min: 6, message: '密码至少6个字符!' }
          ]}
        >
          <Input.Password 
            prefix={<LockOutlined />} 
            placeholder="请输入密码"
            size="large"
          />
        </Form.Item>

        <Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            loading={loading}
            block
            size="large"
          >
            {isRegistering ? '注册' : '登录'}
          </Button>
        </Form.Item>

        <Form.Item style={{ marginBottom: 0, textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <span>{isRegistering ? '已有账号？' : '没有账号？'}</span>
            <Button 
              type="link" 
              onClick={() => setIsRegistering(!isRegistering)}
              style={{ padding: 0 }}
            >
              {isRegistering ? '立即登录' : '立即注册'}
            </Button>
          </div>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default Login;
