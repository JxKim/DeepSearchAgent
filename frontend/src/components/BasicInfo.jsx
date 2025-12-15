import React from 'react';
import { Card, Descriptions, Typography } from 'antd';

const { Title } = Typography;

const BasicInfo = ({ user }) => {
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
      </Card>
    </div>
  );
};

export default BasicInfo;