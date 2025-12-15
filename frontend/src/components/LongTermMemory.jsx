import React, { useState } from 'react';
import { Card, List, Button, Typography, message } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

const { Title } = Typography;

// 模拟数据
const mockMemories = [
  {
    id: 1,
    content: '喜欢阅读科技类书籍'
  },
  {
    id: 2,
    content: '对人工智能领域有浓厚兴趣'
  },
  {
    id: 3,
    content: '偏好使用Python进行编程'
  },
  {
    id: 4,
    content: '经常访问技术博客和论坛'
  },
  {
    id: 5,
    content: '喜欢参与开源项目'
  }
];

const LongTermMemory = () => {
  const [memories, setMemories] = useState(mockMemories);

  const handleDelete = (memoryId) => {
    message.success('记忆已删除');
    setMemories(memories.filter(memory => memory.id !== memoryId));
  };

  return (
    <div className="long-term-memory-container">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <Title level={2} style={{ margin: 0, color: 'var(--text-primary)' }}>长期记忆</Title>
      </div>
      <Card className="long-term-memory-card" bordered={false}>
        <List
          dataSource={memories}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button 
                  type="text" 
                  danger 
                  icon={<DeleteOutlined />} 
                  onClick={() => handleDelete(item.id)}
                >
                  删除
                </Button>
              ]}
            >
              <List.Item.Meta
                title={item.content}
              />
            </List.Item>
          )}
          bordered
        />
      </Card>
    </div>
  );
};

export default LongTermMemory;