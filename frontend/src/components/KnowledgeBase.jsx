import React, { useState, useEffect } from 'react';
import { 
  Card, Table, Button, Typography, message, Modal, Input, List, Tag, Empty, 
  Layout, Menu, Form, Space, Upload, Select, Radio, Badge, Tooltip, Steps,
  Cascader, InputNumber
} from 'antd';
import { 
  SyncOutlined, ExperimentOutlined, SearchOutlined, PlusOutlined, 
  FolderOutlined, UploadOutlined, FileTextOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, LoadingOutlined,
  FilePdfOutlined, FileWordOutlined, FileUnknownOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Sider, Content } = Layout;
const { Option } = Select;

// --- 枚举定义 ---
const ParseStatus = {
  WAITING: 'waiting',     // 等待解析中
  PARSING: 'parsing',     // 解析中
  SUCCESS: 'success',     // 解析成功
  FAILURE: 'failure'      // 解析失败
};

const RetrievalStrategy = {
  HYBRID: 'hybrid',       // 混合检索
  FULLTEXT: 'fulltext',   // 全文检索
  VECTOR: 'vector'        // 向量检索
};

// --- Mock 数据与服务层 (后续替换为真实 API 调用) ---
// 注意：在真实对接时，只需替换这一层的实现即可
const MockService = {
  // 模拟延迟
  delay: (ms) => new Promise(resolve => setTimeout(resolve, ms)),

  // 获取分类列表
  getCategories: async () => {
    await MockService.delay(500);
    return [
      { id: '1', name: '产品文档', count: 3, description: '包含所有产品的详细规格说明书、用户手册及版本更新记录。' },
      { id: '2', name: '技术规范', count: 2, description: '系统架构设计、API 接口文档、数据库设计规范等技术资料。' },
      { id: '3', name: '运营资料', count: 0, description: '市场推广方案、运营活动策划案及相关数据报表。' },
    ];
  },

  // 创建分类
  createCategory: async (name, description) => {
    await MockService.delay(500);
    return { id: Date.now().toString(), name, description, count: 0 };
  },

  // 删除分类
  deleteCategory: async (_categoryId) => {
    await MockService.delay(500);
    return true;
  },

  // 获取分类下的文件
  getFiles: async (categoryId) => {
    await MockService.delay(600);
    // 简单模拟不同分类下的文件
    if (categoryId === '1') {
      return [
        {
          id: 1,
          filename: '产品手册_v1.0.pdf',
          uploadTime: Date.now() - 3600000,
          parseStatus: ParseStatus.SUCCESS,
          parseTime: Date.now() - 3000000,
          chunkCount: 15,
        },
        {
          id: 2,
          filename: '竞品分析.docx',
          uploadTime: Date.now() - 7200000,
          parseStatus: ParseStatus.WAITING,
          parseTime: null,
          chunkCount: 0,
        }
      ];
    }
    return [];
  },

  // 上传文件
  uploadFile: async (categoryId, file) => {
    await MockService.delay(1000);
    return {
      id: Date.now(),
      filename: file.name,
      uploadTime: Date.now(),
      parseStatus: ParseStatus.WAITING,
      parseTime: null,
      chunkCount: 0,
    };
  },

  // 开始解析
  startParse: async (_fileId) => {
    await MockService.delay(500); // 模拟请求启动
    return true;
  },

  // 轮询/获取解析状态 (模拟解析过程)
  checkParseStatus: async (_fileId) => {
    await MockService.delay(2000); // 模拟解析耗时
    // 模拟 90% 成功率
    const isSuccess = Math.random() > 0.1;
    return {
      status: isSuccess ? ParseStatus.SUCCESS : ParseStatus.FAILURE,
      chunkCount: isSuccess ? Math.floor(Math.random() * 50) + 1 : 0,
      parseTime: Date.now()
    };
  },

  // 召回测试
  testRecall: async (query, strategy, _fileId, limit = 3) => {
    await MockService.delay(800);
    // 模拟返回结果
    if (query.includes('空')) return [];
    
    // 根据 limit 生成模拟数据
    return Array.from({ length: limit }).map((_, index) => ({
      file_name: '测试文档.pdf',
      score: 0.95 - (index * 0.1), // 模拟分数递减
      content: `[Chunk ${index + 1}] 这是根据策略 [${strategy}] 召回的关于 "${query}" 的第 ${index + 1} 条相关内容片段... 这里包含了详细的上下文信息。`,
    }));
  },
  
  // 获取所有文件（用于级联选择）
  getAllFilesForSelect: async () => {
    await MockService.delay(300);
    // 模拟数据结构：分类 -> 文件
    return [
      {
        value: '1',
        label: '产品文档',
        children: [
          { value: 1, label: '产品手册_v1.0.pdf' },
          { value: 2, label: '竞品分析.docx' }
        ]
      },
      {
        value: '2',
        label: '技术规范',
        children: [
          { value: 3, label: 'API接口文档.md' },
          { value: 4, label: '数据库设计.sql' }
        ]
      },
      {
        value: '3',
        label: '运营资料',
        isLeaf: true, // 无子节点
        disabled: true // 禁用
      }
    ];
  }
};

const KnowledgeBase = () => {
  // --- 状态管理 ---
  const [categories, setCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  
  // 新建分类相关
  const [isCategoryModalVisible, setIsCategoryModalVisible] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDesc, setNewCategoryDesc] = useState('');
  const [creatingCategory, setCreatingCategory] = useState(false);

  // 上传相关
  const [uploading, setUploading] = useState(false);

  // 召回测试相关
  const [isTestModalVisible, setIsTestModalVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Step 1: 选择文档
  const [fileOptions, setFileOptions] = useState([]);
  const [selectedTestDoc, setSelectedTestDoc] = useState([]); // [categoryId, fileId]

  // Step 2: 策略配置
  const [testStrategy, setTestStrategy] = useState(RetrievalStrategy.HYBRID);
  const [testLimit, setTestLimit] = useState(3);

  // Step 3: 测试结果
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState([]);
  const [isTesting, setIsTesting] = useState(false);

  // --- 初始化加载 ---
  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    if (selectedCategoryId) {
      loadFiles(selectedCategoryId);
    } else {
      setFiles([]);
    }
  }, [selectedCategoryId]);

  // 加载级联选择器数据
  useEffect(() => {
    if (isTestModalVisible) {
      loadFileOptions();
      setCurrentStep(0);
      setTestResults([]);
      setTestQuery('');
    }
  }, [isTestModalVisible]);

  // --- 业务逻辑方法 ---

  const loadCategories = async () => {
    try {
      const data = await MockService.getCategories();
      setCategories(data);
      if (data.length > 0 && !selectedCategoryId) {
        setSelectedCategoryId(data[0].id);
      }
    } catch {
      message.error('加载分类失败');
    }
  };

  const loadFiles = async (categoryId) => {
    setLoadingFiles(true);
    try {
      const data = await MockService.getFiles(categoryId);
      setFiles(data);
    } catch {
      message.error('加载文件失败');
    } finally {
      setLoadingFiles(false);
    }
  };

  const loadFileOptions = async () => {
    try {
      const options = await MockService.getAllFilesForSelect();
      setFileOptions(options);
    } catch (error) {
      console.error('加载文件选项失败', error);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) {
      message.warning('请输入分类名称');
      return;
    }
    setCreatingCategory(true);
    try {
      const newCategory = await MockService.createCategory(newCategoryName, newCategoryDesc);
      setCategories([...categories, newCategory]);
      message.success('分类创建成功');
      setIsCategoryModalVisible(false);
      setNewCategoryName('');
      setNewCategoryDesc('');
      // 自动选中新分类
      setSelectedCategoryId(newCategory.id);
    } catch {
      message.error('创建失败');
    } finally {
      setCreatingCategory(false);
    }
  };

  const handleDeleteCategory = () => {
    if (!selectedCategoryId) return;
    
    const category = categories.find(c => c.id === selectedCategoryId);
    
    Modal.confirm({
      title: '确认删除知识库分类?',
      icon: <DeleteOutlined style={{ color: 'red' }} />,
      content: (
        <div>
          <p>您正在删除分类：<Text strong>{category?.name}</Text></p>
          <p style={{ color: '#ff4d4f' }}>注意：此操作不可恢复，该分类下的所有文件也将被一并删除。</p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await MockService.deleteCategory(selectedCategoryId);
          const newCategories = categories.filter(c => c.id !== selectedCategoryId);
          setCategories(newCategories);
          
          if (newCategories.length > 0) {
            setSelectedCategoryId(newCategories[0].id);
          } else {
            setSelectedCategoryId(null);
          }
          message.success('分类已删除');
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  // 模拟文件上传
  const handleUpload = async (file) => {
    if (!selectedCategoryId) {
      message.warning('请先选择一个分类');
      return false;
    }

    setUploading(true);
    try {
      // 1. 上传文件
      const newFile = await MockService.uploadFile(selectedCategoryId, file);
      const updatedFiles = [newFile, ...files];
      setFiles(updatedFiles);
      message.success('文件上传成功');

      // 2. 询问是否解析
      Modal.confirm({
        title: '是否立即解析?',
        content: `文件 "${newFile.filename}" 已上传，是否立即开始解析？`,
        okText: '立即解析',
        cancelText: '稍后',
        onOk: () => handleParse(newFile.id),
      });

    } catch {
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
    return false; // 阻止 Antd Upload 默认上传行为
  };

  // 解析流程
  const handleParse = async (fileId) => {
    // 1. 更新状态为"解析中"
    updateFileStatus(fileId, { parseStatus: ParseStatus.PARSING });
    
    try {
      // 2. 触发解析任务
      await MockService.startParse(fileId);
      
      // 3. 模拟异步解析过程 (真实场景可能是轮询或 WebSocket)
      // 这里我们在前端模拟一个延迟后获取结果
      setTimeout(async () => {
        try {
          const result = await MockService.checkParseStatus(fileId);
          updateFileStatus(fileId, {
            parseStatus: result.status,
            chunkCount: result.chunkCount,
            parseTime: result.parseTime
          });
          if (result.status === ParseStatus.SUCCESS) {
            message.success('解析完成');
          } else {
            message.error('解析失败');
          }
        } catch {
          updateFileStatus(fileId, { parseStatus: ParseStatus.FAILURE });
        }
      }, 3000);

    } catch {
      message.error('启动解析失败');
      updateFileStatus(fileId, { parseStatus: ParseStatus.FAILURE });
    }
  };

  const updateFileStatus = (fileId, updates) => {
    setFiles(prevFiles => prevFiles.map(f => 
      f.id === fileId ? { ...f, ...updates } : f
    ));
  };

  const handleTestSearch = async () => {
    if (!testQuery.trim()) return;
    if (selectedTestDoc.length < 2) {
      message.warning('请先选择测试文档');
      return;
    }
    
    setIsTesting(true);
    try {
      const fileId = selectedTestDoc[1]; // 选中的是第二级(文件ID)
      const results = await MockService.testRecall(testQuery, testStrategy, fileId, testLimit);
      setTestResults(results);
      if (results.length === 0) {
        message.info('未找到相关内容');
      }
    } catch {
      message.error('测试请求失败');
    } finally {
      setIsTesting(false);
    }
  };

  // --- 渲染辅助函数 ---

  const getStatusTag = (status) => {
    switch (status) {
      case ParseStatus.WAITING:
        return <Tag icon={<ClockCircleOutlined />} color="default">等待解析</Tag>;
      case ParseStatus.PARSING:
        return <Tag icon={<SyncOutlined spin />} color="processing">解析中</Tag>;
      case ParseStatus.SUCCESS:
        return <Tag icon={<CheckCircleOutlined />} color="success">解析成功</Tag>;
      case ParseStatus.FAILURE:
        return <Tag icon={<CloseCircleOutlined />} color="error">解析失败</Tag>;
      default:
        return <Tag>未知状态</Tag>;
    }
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => <Space><FileTextOutlined />{text}</Space>
    },
    {
      title: '上传时间',
      dataIndex: 'uploadTime',
      key: 'uploadTime',
      render: (timestamp) => new Date(timestamp).toLocaleString()
    },
    {
      title: '解析状态',
      dataIndex: 'parseStatus',
      key: 'parseStatus',
      render: (status) => getStatusTag(status)
    },
    {
      title: 'Chunk数量',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      align: 'center',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            size="small"
            disabled={record.parseStatus === ParseStatus.PARSING || record.parseStatus === ParseStatus.SUCCESS}
            onClick={() => handleParse(record.id)}
          >
            {record.parseStatus === ParseStatus.SUCCESS ? '重新解析' : '解析'}
          </Button>
          <Button type="link" danger size="small">删除</Button>
        </Space>
      )
    }
  ];

  // 渲染召回测试步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // 选择文档
        return (
          <div style={{ padding: '24px 0', minHeight: '200px' }}>
            <Form layout="vertical">
              <Form.Item label="选择测试文档 (从已上传文档中选择)" required>
                <Cascader
                  options={fileOptions}
                  placeholder="请选择: 分类 / 文件"
                  value={selectedTestDoc}
                  onChange={setSelectedTestDoc}
                  style={{ width: '100%' }}
                  size="large"
                  expandTrigger="hover"
                />
              </Form.Item>
              <div style={{ marginTop: 24 }}>
                 {selectedTestDoc.length > 0 && (
                   <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', padding: '12px', borderRadius: '6px' }}>
                     <Space>
                       <CheckCircleOutlined style={{ color: '#52c41a' }} />
                       <Text>已选择文档ID: {selectedTestDoc[1]}</Text>
                     </Space>
                   </div>
                 )}
              </div>
            </Form>
          </div>
        );
      case 1: // 策略配置
        return (
          <div style={{ padding: '24px 0', minHeight: '200px' }}>
            <Form layout="vertical">
              <Form.Item label="召回策略" required>
                <Radio.Group 
                  value={testStrategy} 
                  onChange={e => setTestStrategy(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  style={{ width: '100%' }}
                >
                  <Radio.Button value={RetrievalStrategy.HYBRID} style={{ width: '33%', textAlign: 'center' }}>混合检索</Radio.Button>
                  <Radio.Button value={RetrievalStrategy.FULLTEXT} style={{ width: '33%', textAlign: 'center' }}>全文检索</Radio.Button>
                  <Radio.Button value={RetrievalStrategy.VECTOR} style={{ width: '33%', textAlign: 'center' }}>向量检索</Radio.Button>
                </Radio.Group>
                <div style={{ marginTop: 8, color: '#888', fontSize: '12px' }}>
                  {testStrategy === RetrievalStrategy.HYBRID && '同时使用关键词匹配和向量语义匹配，结果最全面'}
                  {testStrategy === RetrievalStrategy.FULLTEXT && '仅使用关键词匹配，适合精确查找'}
                  {testStrategy === RetrievalStrategy.VECTOR && '仅使用向量语义匹配，适合模糊查找'}
                </div>
              </Form.Item>
              
              <Form.Item label="返回条数 (Limit)" required>
                <InputNumber 
                  min={1} 
                  max={20} 
                  value={testLimit} 
                  onChange={setTestLimit} 
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Form>
          </div>
        );
      case 2: // 测试召回
        return (
          <div style={{ padding: '24px 0', minHeight: '200px' }}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Card size="small" type="inner" style={{ background: '#fafafa' }}>
                <Space split={<div style={{ width: 1, height: 16, background: '#ddd' }} />}>
                  <Text type="secondary">当前文档: <Text strong>{fileOptions.find(c=>c.value===selectedTestDoc[0])?.children?.find(f=>f.value===selectedTestDoc[1])?.label || selectedTestDoc[1]}</Text></Text>
                  <Text type="secondary">策略: <Tag color="blue">{testStrategy}</Tag></Text>
                  <Text type="secondary">Limit: {testLimit}</Text>
                </Space>
              </Card>

              <Search
                placeholder="输入测试 Query，例如：'如何申请休假'"
                allowClear
                enterButton={<Button type="primary" icon={<SearchOutlined />}>测试召回</Button>}
                size="large"
                onSearch={handleTestSearch}
                loading={isTesting}
              />

              {/* 结果展示 */}
              <List
                header={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text strong>召回结果 ({testResults.length})</Text>
                  </div>
                }
                bordered
                dataSource={testResults}
                renderItem={(item) => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <Text strong style={{ color: '#1890ff' }}>{item.file_name}</Text>
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
            </Space>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="knowledge-base-container" style={{ height: 'calc(100vh - 100px)' }}>
      <div className="page-header" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0, color: 'var(--text-primary)' }}>知识库管理</Title>
        <Button 
          type="primary" 
          icon={<ExperimentOutlined />} 
          onClick={() => setIsTestModalVisible(true)}
        >
          召回测试
        </Button>
      </div>

      <Layout style={{ height: '100%', background: '#fff', border: '1px solid #f0f0f0', borderRadius: '8px', overflow: 'hidden' }}>
        {/* 左侧分类栏 */}
        <Sider width={250} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>知识库分类</Text>
            <Tooltip title="新建分类">
              <Button 
                type="text" 
                icon={<PlusOutlined />} 
                size="small" 
                onClick={() => setIsCategoryModalVisible(true)}
              />
            </Tooltip>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedCategoryId]}
            style={{ borderRight: 0 }}
            onClick={({ key }) => setSelectedCategoryId(key)}
            items={categories.map(cat => ({
              key: cat.id,
              icon: <FolderOutlined />,
              label: (
                <Tooltip title={cat.description || '暂无描述'} placement="right" mouseEnterDelay={0.5}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: 8 }}>{cat.name}</span>
                    <Badge count={cat.count} style={{ backgroundColor: '#f5f5f5', color: '#999', boxShadow: 'none' }} />
                  </div>
                </Tooltip>
              )
            }))}
          />
        </Sider>

        {/* 右侧内容区 */}
        <Content style={{ padding: '24px', overflowY: 'auto' }}>
          {selectedCategoryId ? (
            <>
              <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={4} style={{ margin: 0 }}>
                  {categories.find(c => c.id === selectedCategoryId)?.name || '文件列表'}
                </Title>
                <Space>
                  <Button 
                    danger 
                    icon={<DeleteOutlined />} 
                    onClick={handleDeleteCategory}
                  >
                    删除分类
                  </Button>
                  <Tooltip title="支持 PDF, Markdown, Word, TXT 等格式文档">
                    <Upload 
                      beforeUpload={handleUpload} 
                      showUploadList={false}
                      disabled={uploading}
                    >
                      <Button type="primary" icon={uploading ? <LoadingOutlined /> : <UploadOutlined />}>
                        {uploading ? '上传中...' : '上传文件'}
                      </Button>
                    </Upload>
                  </Tooltip>
                </Space>
              </div>

              <Table 
                columns={columns} 
                dataSource={files} 
                rowKey="id" 
                loading={loadingFiles}
                pagination={false}
              />
            </>
          ) : (
            <Empty description="请选择或创建一个知识库分类" style={{ marginTop: '100px' }} />
          )}
        </Content>
      </Layout>

      {/* 新建分类弹窗 */}
      <Modal
        title="新建知识库分类"
        open={isCategoryModalVisible}
        onOk={handleCreateCategory}
        confirmLoading={creatingCategory}
        onCancel={() => setIsCategoryModalVisible(false)}
      >
        <Form layout="vertical">
          <Form.Item label="分类名称" required>
            <Input 
              placeholder="请输入分类名称，如：产品文档" 
              value={newCategoryName}
              onChange={e => setNewCategoryName(e.target.value)}
            />
          </Form.Item>
          <Form.Item label="描述">
            <Input.TextArea 
              placeholder="简要概述当前知识库所包含的知识内容" 
              value={newCategoryDesc}
              onChange={e => setNewCategoryDesc(e.target.value)}
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 召回测试弹窗 (Step 模式) */}
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
          setCurrentStep(0);
        }}
        width={800}
        destroyOnClose
        footer={
          <div style={{ marginTop: 24, textAlign: 'right' }}>
            {currentStep > 0 && (
              <Button style={{ margin: '0 8px' }} onClick={() => setCurrentStep(currentStep - 1)}>
                上一步
              </Button>
            )}
            {currentStep < 2 && (
              <Button 
                type="primary" 
                onClick={() => setCurrentStep(currentStep + 1)}
                disabled={currentStep === 0 && selectedTestDoc.length < 2}
              >
                下一步
              </Button>
            )}
            {currentStep === 2 && (
              <Button type="primary" onClick={() => setIsTestModalVisible(false)}>
                完成
              </Button>
            )}
          </div>
        }
      >
        <Steps 
          current={currentStep} 
          items={[
            { title: '选择文档', description: '选择需要测试的文档' },
            { title: '策略配置', description: '设定召回方式与数量' },
            { title: '测试召回', description: '输入问题并验证' },
          ]}
          style={{ marginBottom: 24, marginTop: 12 }}
        />
        
        <div style={{ minHeight: '300px' }}>
          {renderStepContent()}
        </div>
      </Modal>
    </div>
  );
};

export default KnowledgeBase;
