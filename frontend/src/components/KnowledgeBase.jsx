import React, { useState } from 'react';
import { Card, Table, Button, Typography, message, Modal, Input, List, Tag, Empty } from 'antd';
import { SyncOutlined, ExperimentOutlined, SearchOutlined } from '@ant-design/icons';
import { safeApi } from '../api';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

// 模拟数据
const mockFiles = [
  {
    id: 1,
    filename: '示例文档1.pdf',
    uploadTime: Date.now() - 3600000,
    parseTime: Date.now() - 3000000,
    chunkCount: 15,
    parsed: true
  },
  {
    id: 2,
    filename: '示例文档2.docx',
    uploadTime: Date.now() - 7200000,
    parseTime: null,
    chunkCount: 0,
    parsed: false
  },
  {
    id: 3,
    filename: '示例文档3.txt',
    uploadTime: Date.now() - 10800000,
    parseTime: Date.now() - 10500000,
    chunkCount: 5,
    parsed: true
  }
];

const KnowledgeBase = () => {
  const [files, setFiles] = useState(mockFiles);
  
  // 召回测试相关状态
  const [isTestModalVisible, setIsTestModalVisible] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState([]);
  const [isTesting, setIsTesting] = useState(false);

  const handleTestSearch = async (value) => {
    if (!value.trim()) return;
    
    setIsTesting(true);
    try {
      const response = await safeApi.post('/knowledge/recall/test', {
        query: value,
        limit: 5
      });
      if (response.data.success) {
        setTestResults(response.data.data);
        if (response.data.data.length === 0) {
          message.info('未找到相关内容');
        }
      }
    } catch (error) {
      console.error('Test failed:', error);
      // safeApi 会处理错误提示
    } finally {
      setIsTesting(false);
    }
  };

  const handleParse = (fileId) => {
    // 模拟解析文件
    message.loading('正在解析文件...', 2).then(() => {
      message.success('文件解析成功');
      setFiles(files.map(file => {
        if (file.id === fileId) {
          return {
            ...file,
            parsed: true,
            parseTime: Date.now(),
            chunkCount: Math.floor(Math.random() * 20) + 1
          };
        }
        return file;
      }));
    });
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => <span>{text}</span>
    },
    {
      title: '上传时间',
      dataIndex: 'uploadTime',
      key: 'uploadTime',
      render: (timestamp) => {
        return new Date(timestamp).toLocaleString();
      }
    },
    {
      title: '解析时间',
      dataIndex: 'parseTime',
      key: 'parseTime',
      render: (timestamp) => {
        return timestamp ? new Date(timestamp).toLocaleString() : '未解析';
      }
    },
    {
      title: 'chunk数量',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      render: (count) => <span>{count}</span>
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button 
          type="primary" 
          icon={<SyncOutlined />}
          onClick={() => handleParse(record.id)}
          disabled={record.parsed}
        >
          {record.parsed ? '已解析' : '解析'}
        </Button>
      )
    }
  ];

  return (
    <div className="knowledge-base-container">
      <div className="page-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0, color: 'var(--text-primary)' }}>知识库</Title>
        <Button 
          type="primary" 
          icon={<ExperimentOutlined />} 
          onClick={() => setIsTestModalVisible(true)}
        >
          召回测试
        </Button>
      </div>
      <Card className="knowledge-base-card" bordered={false}>
        <Table 
          columns={columns} 
          dataSource={files} 
          rowKey="id" 
          pagination={false}
        />
      </Card>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ExperimentOutlined />
            <span>召回效果测试</span>
          </div>
        }
        open={isTestModalVisible}
        onCancel={() => {
          setIsTestModalVisible(false);
          setTestResults([]);
          setTestQuery('');
        }}
        footer={null}
        width={800}
        destroyOnClose
      >
        <div style={{ padding: '20px 0' }}>
          <Search
            placeholder="输入测试 Query，例如：'如何申请休假'"
            allowClear
            enterButton={<Button type="primary" icon={<SearchOutlined />}>测试召回</Button>}
            size="large"
            onSearch={handleTestSearch}
            loading={isTesting}
            style={{ marginBottom: '24px' }}
          />

          <List
            header={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong>召回结果 ({testResults.length})</Text>
                {testResults.length > 0 && <Tag color="blue">Top 5</Tag>}
              </div>
            }
            bordered
            dataSource={testResults}
            locale={{ emptyText: <Empty description="暂无测试结果" /> }}
            renderItem={(item, index) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <Text strong style={{ color: '#1890ff' }}>{item.file_name || '未知文件'}</Text>
                    <Tag color={item.score > 0.7 ? 'green' : item.score > 0.4 ? 'orange' : 'red'}>
                      相似度: {(item.score * 100).toFixed(2)}%
                    </Tag>
                  </div>
                  <div style={{ 
                    background: '#f5f5f5', 
                    padding: '12px', 
                    borderRadius: '6px',
                    fontSize: '13px',
                    color: '#666',
                    lineHeight: '1.6'
                  }}>
                    <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '展开' }} style={{ margin: 0 }}>
                      {item.content}
                    </Paragraph>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </div>
      </Modal>
    </div>
  );
};

export default KnowledgeBase;