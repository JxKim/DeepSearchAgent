import React from 'react';
import { Card, Descriptions, Typography, Button, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { rawApi } from '../api';

const { Title } = Typography;

const BasicInfo = ({ user, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        // Call backend logout API
        await rawApi.post(`/auth/logout?token=${token}`);
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Even if the backend call fails, we should clear local state
    } finally {
      // Clear local storage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      message.success('已退出登录');
      
      // Update parent component state
      if (onLogout) {
        onLogout();
      }
      
      // Navigate to home page
      navigate('/');
    }
  };

  return (
    <div className="basic-info-container">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <Title level={2} style={{ margin: 0, color: 'var(--text-primary)' }}>用户基本信息</Title>
      </div>
      <Card className="basic-info-card" bordered={false}>
        <Descriptions bordered column={1}>
          <Descriptions.Item label="用户名">{user?.username || '未设置'}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user?.email || '未设置'}</Descriptions.Item>
        </Descriptions>
        
        <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
          <Button type="primary" danger size="large" onClick={handleLogout} style={{ minWidth: '120px' }}>
            退出登录
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default BasicInfo;