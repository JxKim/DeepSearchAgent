# 后端任务
## 一、定义知识库相关的接口
现在调整一下我的后端代码。
我的后端，需要添加知识库相关的接口，
在knowledge这个router当中，有如下接口
1、info接口，展示用户所配置的所有外部知识库，每个知识库为一个文件，所包含的信息有：
	file_name
	file_id
	is_parsed：是否解析
	chunk_num
	search_type: hybrid_search, vector_search, keyword_search

2、upload接口，上传文件，支持类型为pdf,word, txt, csv，

3、删除接口,将某个用户的某个文件知识库删除

4、提交解析任务接口，为长耗时任务，提交之后，后端异步返回，后续前端通过轮询方式，来获取到状态

5、获取知识库文件解析状态接口，前端轮询调用，获取到对应文件的解析状态。

基于此，并且基于我的文件架构，为我定义好schema信息，以及写好knowledge_service对应的方法签名，先不要写具体实现

## 二、定义knowledge_service层
1、info：，通过db读取对应用户的所有知识库列表
2、upload：通过opendal，将文件写入到文件系统当中去
3、delete: 在数据库当中将文件进行删除，同时删除文件系统当中的文件
4、submit：提交解析任务，通过线程池的方式去实现，使用线程池当中的线程对文件解析，定义具体的解析逻辑，当解析完成后，更改数据库状态为is_parsed=True
5、get_status：通过db读取对应用户的某个文件的解析状态

## 三、RAG的专业逻辑
对于RAG层面是，需要做什么，需要实现什么？
### 整体流程：
1、使用Langchain对应的loader解析
2、将解析之后的文档，按照搜索类型，保存到相关的数据库当中：
    vector_search: 将每一个chunk保存到向量数据库当中去
    keyword_search: 将相关内容保存到elasticsearch等支持进行keyword_search的数据库当中去
    hybrid_search: 同时将chunk保存到向量数据库，以及将相关内容保存到elasticsearch等支持进行keyword_search的数据库当中去
3、检索：按照对应的类型，去对应的数据库当中去检索，每个检索会得到一个得分，按照混合检索的比例，来对每个检索的得分进行加权，得到最终的检索结果

### RAG评估指标
如何评估RAG模块，整体结果，是否符合预期，
Recall@K：确保关键信息被捞上来了
MRR: 确保最相关的信息排在前面
Latency: 确保检索引擎响应够快。混合检索的请求到返回时间，是否在可接受范围之内


