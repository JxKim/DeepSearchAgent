import React from 'react';
import { Card, Typography, Button, message, Avatar, Divider, Space } from 'antd';
import { useNavigate } from 'react-router-dom';
import { UserOutlined, LogoutOutlined, MailOutlined, IdcardOutlined } from '@ant-design/icons';
import { rawApi } from '../api';

const { Title, Text } = Typography;

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
    <div className="basic-info-container" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div className="page-header" style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <Title level={2} style={{ margin: 0, color: 'var(--text-primary)' }}>个人资料</Title>
        <Text type="secondary">管理您的个人信息和账户安全</Text>
      </div>

      <Card 
        bordered={false} 
        style={{ 
          borderRadius: '16px', 
          boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
          background: '#fff' 
        }}
      >
        {/* 顶部头像区域 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '2rem' }}>
          <Avatar 
            size={100} 
            icon={<UserOutlined />} 
            src={user?.avatar}
            style={{ 
              backgroundColor: '#1677ff', 
              marginBottom: '1rem',
              fontSize: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {user?.username?.[0]?.toUpperCase()}
          </Avatar>
          <Title level={3} style={{ margin: 0, marginBottom: '0.5rem' }}>{user?.username}</Title>
          <Text type="secondary">{user?.email}</Text>
        </div>

        <Divider />

        {/* 信息列表区域 */}
        <div style={{ padding: '0 1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', padding: '1.5rem 0', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ marginRight: '1.5rem', fontSize: '24px', color: '#8c8c8c' }}>
              <IdcardOutlined />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px', color: '#8c8c8c', marginBottom: '4px' }}>用户名</div>
              <div style={{ fontSize: '16px', color: '#262626', fontWeight: 500 }}>{user?.username || '未设置'}</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', padding: '1.5rem 0' }}>
            <div style={{ marginRight: '1.5rem', fontSize: '24px', color: '#8c8c8c' }}>
              <MailOutlined />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px', color: '#8c8c8c', marginBottom: '4px' }}>电子邮箱</div>
              <div style={{ fontSize: '16px', color: '#262626', fontWeight: 500 }}>{user?.email || '未设置'}</div>
            </div>
          </div>
        </div>

        <Divider />

        {/* 底部操作区域 */}
        <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
          <Button 
            size="large" 
            danger 
            icon={<LogoutOutlined />}
            onClick={handleLogout} 
            style={{ 
              minWidth: '160px', 
              height: '48px', 
              borderRadius: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            退出登录
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default BasicInfo;