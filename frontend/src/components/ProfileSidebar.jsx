import React from 'react';
import { Menu, Button } from 'antd';
import { UserOutlined, BookOutlined, DatabaseOutlined, CloseOutlined } from '@ant-design/icons';
import { Typography } from 'antd';

const { Title } = Typography;

const ProfileSidebar = ({ activeTab, setActiveTab, onClose }) => {
  const menuItems = [
    {
      key: 'basic',
      icon: <UserOutlined />,
      label: '用户基本信息',
    },
    {
      key: 'knowledge',
      icon: <BookOutlined />,
      label: '知识库',
    },
    {
      key: 'memory',
      icon: <DatabaseOutlined />,
      label: '长期记忆',
    },
  ];

  return (
    <div className="profile-sidebar-container">
      <div className="sidebar-header">
        <Title level={3} style={{ margin: 0 }}>用户中心</Title>
        <Button 
          type="text" 
          icon={<CloseOutlined />} 
          onClick={onClose}
          style={{ marginLeft: 'auto', color: 'var(--text-secondary)' }}
          className="icon-btn"
        />
      </div>
      <Menu
        mode="inline"
        selectedKeys={[activeTab]}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
        onSelect={({ key }) => setActiveTab(key)}
      />
    </div>
  );
};

export default ProfileSidebar;