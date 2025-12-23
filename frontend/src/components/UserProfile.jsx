import React, { useState } from 'react';
import { Layout } from 'antd';
import ProfileSidebar from './ProfileSidebar';
import BasicInfo from './BasicInfo';
import KnowledgeBase from './KnowledgeBase';
import LongTermMemory from './LongTermMemory';

const { Sider, Content } = Layout;

const UserProfile = ({ user, onClose, onLogout }) => {
  const [activeTab, setActiveTab] = useState('basic');

  const renderContent = () => {
    switch (activeTab) {
      case 'basic':
        return <BasicInfo user={user} onLogout={onLogout} />;
      case 'knowledge':
        return <KnowledgeBase />;
      case 'memory':
        return <LongTermMemory />;
      default:
        return <BasicInfo user={user} onLogout={onLogout} />;
    }
  };

  return (
    <Layout className="user-profile-layout" style={{ height: '100vh' }}>
      <Sider width={250} theme="light" className="profile-sidebar">
        <ProfileSidebar activeTab={activeTab} setActiveTab={setActiveTab} onClose={onClose} />
      </Sider>
      <Content className="profile-content">
        {renderContent()}
      </Content>
    </Layout>
  );
};

export default UserProfile;