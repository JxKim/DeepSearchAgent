# About DeepSearchAgent
## get started
### 前端
通过命令行启动，命令如下：
`cd ./frontend && npm run dev`
### 后端
1. 安装依赖：`cd SmartAgentDemo/backend && uv sync`
2. 复制&&修改配置文件：`cd SmartAgentDemo && cp backend/config.yaml.example config.yaml`
3. 启动：`cd SmartAgentDemo/backend && python main.py`

## features
- [x] 多用户系统
- [x] 多对话，通过checkpointer实现的短期记忆功能，历史会话记录查看功能
- [x] 使用interrupt & command实现的人机协作功能
- [x] web_search,调用接口，将报告内容，写入飞书
## todo-list
### 大功能更新
- [ ] langgraph短期记忆，使用postgresSQL实现，不使用sqllite
- [ ] 使用docker启动前后端项目，所有数据库依赖
- [ ] 添加知识库，需要调整graph整体流程，添加RAG
- [ ] 使用vlm model 进行图像识别 
- [ ] 将项目通过docker compose打包部署
- [ ] 定义不同行业的不同的图流程
- [ ] 长期记忆，基于历史会话记录获取
### 小功能优化
- [ ] 删除会话、会话标题内容优化
- [ ] ...

## 日更记录
2025-12-09
- [x] 使用uv管理项目依赖
- [ ] 数据库依赖，使用docker打包
- [ ] 知识库相关接口定义
- [ ] 知识库相关service层定义：按照langchain当中基本的loader，对数据进行处理