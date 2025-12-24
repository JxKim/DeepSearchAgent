import React, { useState } from 'react';
import { SearchOutlined, CloseOutlined } from '@ant-design/icons';
import './SearchPage.css';

const SearchPage = ({ onSelectSession, sessions = [] }) => {
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // 处理搜索逻辑
  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchText.trim()) {
      const results = sessions.filter(session => {
        const query = searchText.toLowerCase();
        // 搜索会话标题或最后一条消息
        return (
          (session.title && session.title.toLowerCase().includes(query)) ||
          (session.lastMessage && session.lastMessage.toLowerCase().includes(query))
        );
      });
      setSearchResults(results);
      setHasSearched(true);
    }
  };

  // 清除搜索
  const clearSearch = () => {
    setSearchText('');
    setSearchResults([]);
    setHasSearched(false);
  };

  // 格式化日期显示
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  };

  // 显示的内容：搜索结果或近期对话（如果没有搜索）
  const displayItems = hasSearched ? searchResults : sessions.slice(0, 5); // 默认显示最近5条

  return (
    <div className="search-container">
      <div className="search-title">搜索</div>
      
      <div className="search-box-wrapper">
        <SearchOutlined className="search-icon" />
        <input
          className="search-input"
          type="text"
          placeholder="搜索对话"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onKeyDown={handleSearch}
          autoFocus
        />
        {searchText && (
          <div className="search-clear-btn" onClick={clearSearch}>
            <CloseOutlined />
          </div>
        )}
      </div>

      <div className="search-results">
        {hasSearched && (
          <div className="search-result-count">
            {searchResults.length} 条与"{searchText}"相符的搜索结果
          </div>
        )}

        {!hasSearched && sessions.length > 0 && (
          <div className="recent-searches-title">近期对话</div>
        )}

        {displayItems.map(item => (
          <div 
            key={item.id} 
            className="search-result-item"
            onClick={() => onSelectSession(item.id)}
          >
            <div className="search-result-content">
              <div className="search-result-title">{item.title || '新对话'}</div>
              <div className="search-result-desc">{item.lastMessage || '暂无消息'}</div>
            </div>
            <div className="search-result-date">
              {formatDate(item.updated_at || item.created_at)}
            </div>
          </div>
        ))}

        {hasSearched && searchResults.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '2rem' }}>
            未找到相关结果
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
