// 渲染tab+点击高亮实现
// lodash 可以实现排序功能
// 什么叫做获取DOM
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
// 样式控制：行内样式，或者是通过CSS来控制样式，然后去引入，通过className的方式来
import './App.css';
import './components/DeleteNotification.css';
import './components/LoginButton.css';
import Login from './components/Login.jsx';
import UserProfile from './components/UserProfile.jsx';
import SearchPage from './components/SearchPage.jsx';
import api, { stopGeneration } from './api.js';
import { handleApiError } from './utils/errorHandler';
import { message, Input, Button, Space, Typography, Dropdown } from 'antd';
import { SendOutlined, PauseOutlined, LoadingOutlined, UserOutlined, MenuOutlined, SearchOutlined, EditOutlined, ShareAltOutlined, PushpinOutlined, DeleteOutlined } from '@ant-design/icons';

// 在react中，一个组件就是一个首字母大写的函数，内部存放了组件的逻辑和视图UI，渲染组件只需要
// 只要是个函数，不管是什么形式，例如是通过function形式定义的，或者是通过箭头匿名函数，也行

function App() {
  // useState执行之后的结果是数组，user是状态变量，setUser是修改状态变量的方法：通过状态变量，驱动视图变化
  // 用户认证状态
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  
  // 聊天历史记录状态
  const [chatHistory, setChatHistory] = useState([]);
  
  // 当前聊天记录状态
  const [currentChat, setCurrentChat] = useState([]);
  
  // 当前选中的会话ID
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  
  // 新消息输入状态
  const [newMessage, setNewMessage] = useState('');
  
  // 函数调用弹窗状态
  const [showFuncCallModal, setShowFuncCallModal] = useState(false);
  const [currentFuncCall, setCurrentFuncCall] = useState(null);
  
  // 跟踪哪些AI消息的tool_messages是展开的
  const [expandedToolMessages, setExpandedToolMessages] = useState({});
  
  // 暂停生成功能相关状态
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStreamController, setCurrentStreamController] = useState(null);
  const [pausedMessageId, setPausedMessageId] = useState(null);

  // 侧边栏折叠状态
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 搜索页面显示状态
  const [showSearch, setShowSearch] = useState(false);

  // 删除提示状态
  const [deleteNotification, setDeleteNotification] = useState(null);

  // 获取聊天会话历史
  const fetchChatSessions = async () => {
    try {
      const response = await api.get('/sessions');
      // 会话列表在response.data.data中
      const sessions = response.data.data || [];
      setChatHistory(sessions);
      
      // 如果有会话，默认选择第一个
      if (sessions.length > 0 && !selectedSessionId) {
        handleSelectSession(sessions[0].id);
      }
    } catch (error) {
      console.log(error);
      handleApiError(error, { 
        showMessage: true,
        customMessage: '获取聊天会话失败'
      });
    }
  };

  // 获取特定会话的消息
  const fetchSessionMessages = async (sessionId) => {
    try {
      const response = await api.get(`/sessions/${sessionId}/messages`);
      setCurrentChat(response.data);
    } catch (error) {
      console.log(error);
      handleApiError(error, { 
        showMessage: true,
        customMessage: '获取会话消息失败'
      });
    }
  };

  // 处理选择会话
  const handleSelectSession = async (sessionId) => {
    setSelectedSessionId(sessionId);
    setShowSearch(false); // 选中会话后关闭搜索页面
    await fetchSessionMessages(sessionId);
  };

  // 暂停生成
  const handleStopGeneration = async () => {
    if (!isGenerating || !selectedSessionId) return;

    try {
      // 中断流式响应
      if (currentStreamController) {
        currentStreamController.abort();
        setCurrentStreamController(null);
      }

      // 调用后端暂停接口
      await stopGeneration(selectedSessionId);
      
      // 更新状态
      setIsGenerating(false);
      setPausedMessageId(null);
      
      message.success('生成已暂停');
    } catch (error) {
      // stopGeneration已经内置了错误处理，这里不需要重复处理
    }
  };

  // 发送新消息
  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedSessionId) return;

    try {
      // 先将用户消息添加到本地聊天记录
      const userMessage = {
        id: Date.now().toString(),
        text: newMessage,
        sender: 'user',
        timestamp: new Date().toISOString()
      };
      setCurrentChat(prev => [...prev, userMessage]);
      
      // 更新会话列表中的最后消息
      setChatHistory(prev => prev.map(session => 
        session.id === selectedSessionId 
          ? { ...session, lastMessage: newMessage, timestamp: new Date().toLocaleTimeString('zh-CN', { 
              hour: '2-digit', 
              minute: '2-digit', 
              second: '2-digit' 
            }) }
          : session
      ));
      
      // 清空输入框
      setNewMessage('');
      
      // 创建一个临时ID用于AI回复
      const aiMessageId = `ai-${Date.now()}`;
      
      // 添加一个空的AI消息占位符，使用sections数组存储所有消息段落（ai_message和tool_message）
      setCurrentChat(prev => [...prev, {
        id: aiMessageId,
        sections: [], // 存储所有消息段落，每个段落包含type和content
        sender: 'agent',
        timestamp: new Date().toISOString(),
        tool_messages: [] // 兼容旧格式
      }]);
      
      // 创建AbortController用于中断流式响应
      const abortController = new AbortController();
      setCurrentStreamController(abortController);
      setIsGenerating(true);
      setPausedMessageId(aiMessageId);

      // 使用fetch API直接处理流式响应，不使用axios
      const baseURL = import.meta.env.VITE_API_URL;
      const response = await fetch(`${baseURL}/sessions/${selectedSessionId}/messages/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          text: newMessage,
          metadata: {},
          sender: 'user'
        }),
        signal: abortController.signal,
        // credentials: 'include', // 发送凭据，处理CORS
        // mode: 'cors' // 显式设置为cors模式
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 处理流式响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码新的字节
        buffer += decoder.decode(value, { stream: true });
        
        // 处理每一行SSE数据
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留最后一行不完整的数据
        
        let stopStreaming = false;
        
        for (const line of lines) {
          if (stopStreaming) break;
          
          if (line.trim().startsWith('data :')) {
            // 解析SSE数据行，格式：data : {"ai_message": "内容"} 或 {"func_call": {"to": "...", "subject": "...", "body": "..."}}
            try {
              const jsonStr = line.trim().slice(7); // 去掉 "data : " 前缀
              const data = JSON.parse(jsonStr);
              
              if (data.ai_message) {
                // 更新accumulatedText变量
                accumulatedText += data.ai_message;
                
                // 只在消息不重复时添加内容
                setCurrentChat(prev => prev.map(msg => {
                  if (msg.id === aiMessageId) {
                    const updatedSections = [...msg.sections];
                    let lastSection = updatedSections[updatedSections.length - 1];
                    
                    if (lastSection && lastSection.type === 'ai_message') {
                      // 检查当前消息片段是否已经包含在现有内容中，避免重复
                      if (!lastSection.content.includes(data.ai_message)) {
                        lastSection.content += data.ai_message;
                      }
                    } else {
                      // 否则创建一个新的ai_message section
                      updatedSections.push({ type: 'ai_message', content: data.ai_message });
                    }
                    
                    return { ...msg, sections: updatedSections };
                  }
                  return msg;
                }));
              } else if (data.tool_message) {
                // 将tool_message添加到sections数组中
                setCurrentChat(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { 
                        ...msg, 
                        sections: [...msg.sections, { type: 'tool_message', content: data.tool_message }] 
                      }
                    : msg
                ));
              } else if (data.func_call && typeof data.func_call === 'object') {
                // 检测到函数调用请求，显示弹窗
                setCurrentFuncCall(data.func_call);
                setShowFuncCallModal(true);
                
                // 停止当前流式响应处理，因为后续响应会由handleToolCall处理
                stopStreaming = true;
                break;
              }
            } catch (error) {
              // 解析SSE数据失败，继续处理下一行，避免整个应用崩溃
              // 这里不显示用户提示，因为这是内部数据处理错误
            }
          }
        }
        
        if (stopStreaming) {
          // 停止流式响应处理
          await reader.cancel();
          break;
        }
      }
      
      // 流式响应结束后，更新会话列表中的最后消息
      setChatHistory(prev => prev.map(session => 
        session.id === selectedSessionId 
          ? { ...session, lastMessage: accumulatedText, timestamp: new Date().toLocaleTimeString('zh-CN', { 
              hour: '2-digit', 
              minute: '2-digit', 
              second: '2-digit' 
            }) }
          : session
      ));
      
      // 重置生成状态
      setIsGenerating(false);
      setCurrentStreamController(null);
      setPausedMessageId(null);
    } catch (error) {
      // 使用统一的错误处理系统
      handleApiError(error, { 
        showMessage: true,
        customMessage: '发送消息失败，请稍后重试'
      });
      // 重置生成状态
      setIsGenerating(false);
      setCurrentStreamController(null);
      setPausedMessageId(null);
    }
  };

  // 处理工具调用请求
  const handleToolCall = async (isAuthorized) => {
    if (!selectedSessionId || !currentFuncCall) return;

    try {
      // 调用后端工具调用接口
      const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const response = await fetch(`${baseURL}/sessions/${selectedSessionId}/messages/tools`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          tool_name: 'send_email',
          parameters: currentFuncCall,
          is_authorized: isAuthorized
        }),
        // credentials: 'include', // 发送凭据，处理CORS
        // mode: 'cors' // 显式设置为cors模式
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 处理流式响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      // 找到当前AI消息，用于更新sections字段
      const aiMessages = currentChat.filter(msg => msg.sender === 'agent');
      const lastAiMessageId = aiMessages[aiMessages.length - 1]?.id;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码新的字节
        buffer += decoder.decode(value, { stream: true });
        
        // 按行分割数据
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留最后一行不完整的数据
        
        for (const line of lines) {
          if (line.trim().startsWith('data :')) {
            // 解析SSE数据行
            try {
              const jsonStr = line.trim().slice(7); // 去掉 "data : " 前缀
              const data = JSON.parse(jsonStr);
              
              if (data.ai_message) {
                // 只在消息不重复时添加内容
                if (lastAiMessageId) {
                  setCurrentChat(prev => prev.map(msg => {
                    if (msg.id === lastAiMessageId) {
                      const updatedSections = [...msg.sections];
                      let lastSection = updatedSections[updatedSections.length - 1];
                       
                      if (lastSection && lastSection.type === 'ai_message') {
                        // 检查当前消息片段是否已经包含在现有内容中，避免重复
                        if (!lastSection.content.includes(data.ai_message)) {
                          lastSection.content += data.ai_message;
                        }
                      } else {
                        // 否则创建一个新的ai_message section
                        updatedSections.push({ type: 'ai_message', content: data.ai_message });
                      }
                       
                      return { ...msg, sections: updatedSections };
                    }
                    return msg;
                  }));
                }
              } else if (data.tool_message) {
                // 将tool_message添加到sections数组中
                if (lastAiMessageId) {
                  setCurrentChat(prev => prev.map(msg => 
                    msg.id === lastAiMessageId 
                      ? { 
                          ...msg, 
                          sections: [...msg.sections, { type: 'tool_message', content: data.tool_message }] 
                        }
                      : msg
                  ));
                }
              }
            } catch (error) {
              // 解析SSE数据失败，继续处理下一行，避免整个应用崩溃
              // 这里不显示用户提示，因为这是内部数据处理错误
            }
          }
        }
      }
      
      // 流式响应结束后，更新会话列表中的最后消息
      // 找到当前AI消息，提取最后一个ai_message作为会话的最后消息
      setChatHistory(prev => {
        // 从当前聊天记录中找到最后一条AI消息
        const currentAI = currentChat.filter(msg => msg.sender === 'agent').pop();
        let lastMessage = '';
        if (currentAI) {
          if (currentAI.sections && currentAI.sections.length > 0) {
            // 找到最后一个ai_message
            const lastAiSection = currentAI.sections.filter(section => section.type === 'ai_message').pop();
            if (lastAiSection) {
              lastMessage = lastAiSection.content;
            }
          } else if (currentAI.text) {
            // 兼容旧格式的AI消息
            lastMessage = currentAI.text;
          }
        }
        
        return prev.map(session => 
          session.id === selectedSessionId 
            ? { ...session, lastMessage: lastMessage, timestamp: new Date().toLocaleTimeString('zh-CN', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
              }) }
            : session
        );
      });
    } catch (error) {
      // 使用统一的错误处理系统
      handleApiError(error, { 
        showMessage: true,
        customMessage: '处理工具调用失败'
      });
    }
  };

  // 创建新会话
  const handleCreateSession = async () => {
    try {
      const response = await api.post('/sessions', {
        title: `新会话 ${chatHistory.length + 1}`
      });
      
      // 更新会话列表，将新会话添加到开头
      const newSession = response.data;
      setChatHistory(prev => [newSession, ...prev]);
      
      // 选择新创建的会话
      handleSelectSession(newSession.id);
    } catch (error) {
      // 使用统一的错误处理系统
      handleApiError(error, { 
        showMessage: true,
        customMessage: '创建会话失败'
      });
    }
  };

  // 用户认证相关函数
  const handleLogin = (userData) => {
    setUser(userData);
    // 登录成功后，立即获取会话列表
    fetchChatSessions();
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setChatHistory([]);
    setCurrentChat([]);
    setSelectedSessionId(null);
  };

  // 组件挂载时获取初始数据和检查登录状态
  useEffect(() => {
    // 检查本地存储中是否有用户信息
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        setUser(parsedUser);
        // 如果用户已登录，获取会话列表
        fetchChatSessions();
      } catch (error) {
        // 解析用户信息失败，清除本地存储
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        // 这里不显示错误提示，因为这是初始化时的内部错误
      }
    }
  }, []); // 空依赖数组，只在组件挂载时执行一次

  // 选择会话时加载消息，不需要轮询
  useEffect(() => {
    if (selectedSessionId) {
      fetchSessionMessages(selectedSessionId);
    }
  }, [selectedSessionId]); // 当选中的会话ID变化时，一次性加载消息

  // 处理键盘事件
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };
  
  // 处理tool_messages的展开/折叠
  const toggleToolMessages = (messageId) => {
    setExpandedToolMessages(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  // 删除会话
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation(); // 阻止冒泡
    const sessionToDelete = chatHistory.find(s => s.id === sessionId);
    try {
      await api.delete(`/sessions/${sessionId}`);
      
      // 更新本地状态
      setChatHistory(prev => prev.filter(session => session.id !== sessionId));
      
      // 如果删除的是当前选中的会话，则清除选中状态或选择另一个
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
        setCurrentChat([]);
      }
      
      // 显示左下角删除提示
      setDeleteNotification(`已删除“${sessionToDelete?.title || '会话'}”`);
      
      // 3秒后自动消失
      setTimeout(() => {
        setDeleteNotification(null);
      }, 3000);
      
    } catch (error) {
      handleApiError(error, { 
        showMessage: true, 
        customMessage: '删除会话失败' 
      });
    }
  };

  // 切换侧边栏折叠状态
  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <div className="app-container">
      {showProfile ? (
        <UserProfile user={user} onClose={() => setShowProfile(false)} />
      ) : (
        <div className="chat-layout">
          {/* 左侧聊天历史记录 - 侧边栏 */}
          <div className={`chat-history ${isSidebarCollapsed ? 'collapsed' : ''}`}>
            {/* 顶部工具栏：汉堡菜单 + 搜索 */}
            <div className="sidebar-header-tools">
              <Button 
                type="text" 
                icon={<MenuOutlined />} 
                className="icon-btn menu-btn" 
                onClick={toggleSidebar}
              />
              {!isSidebarCollapsed && (
                <Button 
                  type="text" 
                  icon={<SearchOutlined />} 
                  className="icon-btn search-btn" 
                  onClick={() => setShowSearch(true)}
                />
              )}
            </div>

            {/* 发起新对话按钮 */}
            <div className="new-chat-wrapper">
              <Button 
                type="text" 
                icon={<EditOutlined />} 
                className={`new-chat-btn ${isSidebarCollapsed ? 'collapsed' : ''}`}
                onClick={handleCreateSession}
              >
                {!isSidebarCollapsed && '发起新对话'}
              </Button>
            </div>

            {/* 对话列表区域 */}
            <div className="history-list-container">
              {!isSidebarCollapsed && <div className="history-section-title">对话</div>}
              {!isSidebarCollapsed && (
                <div className="history-list">
                  {chatHistory.map(chat => (
                    <div 
                      key={chat.id} 
                      className={`history-item ${selectedSessionId === chat.id ? 'active' : ''}`}
                      onClick={() => handleSelectSession(chat.id)}
                    >
                    <div className="history-title-row">
                      <div className="history-title">{chat.title}</div>
                      <div className="history-actions">
                        <Dropdown
                          menu={{
                            items: [
                              {
                                key: 'share',
                                label: '分享对话内容',
                                icon: <ShareAltOutlined />
                              },
                              {
                                key: 'pin',
                                label: '固定',
                                icon: <PushpinOutlined />
                              },
                              {
                                key: 'rename',
                                label: '重命名',
                                icon: <EditOutlined />
                              },
                              {
                                key: 'delete',
                                label: '删除',
                                icon: <DeleteOutlined />,
                                onClick: (e) => handleDeleteSession(e.domEvent, chat.id)
                              }
                            ]
                          }}
                          trigger={['click']}
                          placement="bottomRight"
                          overlayClassName="custom-dropdown"
                        >
                          <button 
                            className="more-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              // 阻止事件冒泡，防止触发选中会话
                            }}
                          >
                            <svg viewBox="64 64 896 896" focusable="false" data-icon="more" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M456 231a56 56 0 10112 0 56 56 0 10-112 0zm0 280a56 56 0 10112 0 56 56 0 10-112 0zm0 280a56 56 0 10112 0 56 56 0 10-112 0z"></path></svg>
                          </button>
                        </Dropdown>
                      </div>
                    </div>
                    {/* <div className="history-time">{chat.timestamp}</div> */}
                  </div>
                ))}
              </div>
              )}
            </div>
          </div>

          {/* 右侧当前聊天窗口或搜索页面 */}
          <div className="chat-window">
            {showSearch ? (
              <SearchPage 
                sessions={chatHistory} 
                onSelectSession={handleSelectSession} 
              />
            ) : (
              <>
                <div className="chat-header">
                  <h2 className="chat-header-title">
                    {chatHistory.find(s => s.id === selectedSessionId)?.title || '请选择一个会话'}
                  </h2>
                  <div className="user-info">
                    {user ? (
                      <Space>
                        <div 
                          className="user-avatar"
                          onClick={() => setShowProfile(true)}
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            backgroundColor: '#1677ff', // 基本色
                            color: '#fff',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            fontSize: '16px',
                            fontWeight: 'bold'
                          }}
                        >
                          {user.username.charAt(0).toUpperCase()}
                        </div>
                      </Space>
                    ) : (
                      <Button 
                        className="login-btn"
                        onClick={() => setShowLogin(true)}
                      >
                        登录
                      </Button>
                    )}
                  </div>
                </div>
                
                {currentChat.length === 0 ? (
                  <div className="welcome-screen">
                    <h1 className="welcome-title">需要我为你研究些什么？</h1>
                  </div>
                ) : (
                  <div className="chat-messages">
                    {currentChat.map((message, index) => (
                      <div key={message.id} className={`message ${message.sender}`}>
                        <div className="message-content-wrapper">
                          {message.sender === 'agent' && (
                            <div className="avatar">
                              {isGenerating && index === currentChat.length - 1 ? (
                                <div className="agent-avatar-loading">
                                  <div className="agent-avatar-loading-icon">✦</div>
                                </div>
                              ) : (
                                <div className="agent-avatar-completed">
                                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill={`url(#paint0_linear_${message.id})`} />
                                    <defs>
                                      <linearGradient id={`paint0_linear_${message.id}`} x1="12" y1="2" x2="12" y2="21.02" gradientUnits="userSpaceOnUse">
                                        <stop stopColor="#4285F4"/>
                                        <stop offset="1" stopColor="#9B72CB"/>
                                      </linearGradient>
                                    </defs>
                                  </svg>
                                </div>
                              )}
                            </div>
                          )}
                          <div className="message-text">
                            {message.sender === 'agent' ? (
                              <>
                                {/* 按照sections数组的顺序渲染每个消息段落 */}
                                
                                {message.sections && message.sections.length > 0 ? (
                                  message.sections.map((section, index) => (
                                    <React.Fragment key={`${message.id}-${section.type}-${index}`}>
                                      {section.type === 'ai_message' ? (
                                        /* 渲染AI消息文本 */
                                        <ReactMarkdown>{section.content}</ReactMarkdown>
                                      ) : (section.type === 'tool_message' && (
                                        /* 渲染可折叠的工具消息，每个工具消息一个独立窗口 */
                                        <div className="tool-messages-container">
                                          <button 
                                            className="tool-messages-toggle"
                                            onClick={() => toggleToolMessages(`${message.id}-tool-${index}`)}
                                          >
                                            {expandedToolMessages[`${message.id}-tool-${index}`] ? '▼ 收起工具消息' : '▶ 查看工具消息'}
                                          </button>
                                          {expandedToolMessages[`${message.id}-tool-${index}`] && (
                                            <div className="tool-messages-content">
                                              <div className="tool-message">
                                                <pre>{JSON.stringify(section.content, null, 2)}</pre>
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </React.Fragment>
                                  ))
                                ) : (
                                  /* 兼容旧格式的AI消息 */
                                  <ReactMarkdown>{message.text || ''}</ReactMarkdown>
                                )}
                              </>
                            ) : (
                              message.text
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="chat-input">
                  {/* 生成指示器 - 使用Ant Design组件 */}
                  {isGenerating && (
                    <div className="generation-controls">
                      <Space size="small">
                        <LoadingOutlined style={{ color: 'var(--primary-color)' }} />
                        <Typography.Text style={{ color: 'var(--text-secondary)' }}>AI正在生成中...</Typography.Text>
                      </Space>
                    </div>
                  )}
                  
                  <div className="message-input-container">
                    <Button 
                      type="text"
                      shape="circle"
                      icon={<span style={{ fontSize: '1.2rem' }}>＋</span>}
                      className="input-action-btn"
                    />
                    <Input 
                      placeholder="DeepSearch一下" 
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={!selectedSessionId || isGenerating}
                      size="large"
                      variant="borderless"
                    />
                    <Button 
                      type={isGenerating ? "text" : "text"}
                      icon={isGenerating ? <PauseOutlined /> : <SendOutlined />}
                      onClick={isGenerating ? handleStopGeneration : handleSendMessage}
                      disabled={!selectedSessionId || (!newMessage.trim() && !isGenerating)}
                      className={`send-btn ${newMessage.trim() ? 'active' : ''}`}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 登录模态框 */}
      {showLogin && (
        <Login 
          onLogin={handleLogin}
          onClose={() => setShowLogin(false)}
        />
      )}
      
      {/* 函数调用确认弹窗 */}
      {showFuncCallModal && currentFuncCall && typeof currentFuncCall === 'object' && (
        <div className="func-call-modal-overlay">
          <div className="func-call-modal">
            <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: '20px' }}>
              函数调用请求
            </Typography.Title>
            <div className="func-call-content">
              <Typography.Paragraph>AI请求调用以下函数：</Typography.Paragraph>
              <div className="func-call-details">
                <Typography.Paragraph><strong>函数名称：</strong>send_email</Typography.Paragraph>
                <Typography.Paragraph><strong>参数：</strong></Typography.Paragraph>
                <ul>
                  {Object.entries(currentFuncCall).map(([key, value]) => (
                    <li key={key}>
                      <strong>{key}：</strong>{typeof value === 'string' ? value : JSON.stringify(value)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button 
                type="primary" 
                size="large"
                style={{ flex: 1, marginRight: '10px' }}
                onClick={async () => {
                  // 同意按钮点击事件
                  setShowFuncCallModal(false);
                  await handleToolCall(true);
                }}
              >
                同意
              </Button>
              <Button 
                type="default" 
                size="large"
                style={{ flex: 1 }}
                onClick={async () => {
                  // 拒绝按钮点击事件
                  setShowFuncCallModal(false);
                  await handleToolCall(false);
                }}
              >
                拒绝
              </Button>
            </Space>
          </div>
        </div>
      )}
      {/* 删除通知弹窗 */}
      {deleteNotification && (
        <div className="delete-notification">
          <span className="delete-notification-text">{deleteNotification}</span>
        </div>
      )}
    </div>
  );
}

export default App;
