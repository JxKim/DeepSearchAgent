"""
Markdown解析器，对Markdown进行解析
"""
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class MarkdownParser(BaseParser):
    """
    Markdown文件解析器
    """
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def parse(self, file_path: str) -> List[Document]:
        """
        通过MineruParser将PDF文件解析成MarkDown之后，再通过MarkdownLoader解析Markdown文件内容，将其切分成不同的chunk，再将chunk内容存储到Milvus当中去
        :param file_path: Markdown文件路径
        :return: 解析后的文本内容
        """
        loader = UnstructuredMarkdownLoader(file_path=file_path,mode="elements")
        documents = loader.load()
        return documents
    
    @staticmethod
    def _clean_markdown(markdown_text: str) -> str:
        """
        对MarkDown文档文本进行清洗：
        1、移除Markdown当中的空行（包括多个连续的空行），空行在原文档当中可能表示换页
        """
        # 移除Markdown中的特殊字符，如反引号、星号等
        # 1、移除多个连续的空行
        cleaned_text = re.sub(r'\n\s*\n', '\n', markdown_text)
        # 2、移除多余的空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        return cleaned_text

    def _enrich_with_breadcrumbs(self,documents:List[Document])->List[dict]:
        """
        为element添加层级信息，通过面包屑（breadcrumb）的方式，将标题信息添加到内容元素中
        """
        # 栈结构用来保存当前的标题层级 [ (level, text), ... ]
        # level: h1=1, h2=2, ...
        header_stack = []
        
        enriched_data = []
        
        for doc in documents:
            
            
            if doc.metadata["category"] == "Title":
                
                # 维护栈：移除所有比当前 depth 深或相同的标题（因为遇到了新的同级或更高级标题）
                while header_stack and header_stack[-1][0] >= current_depth:
                    header_stack.pop()
                
                header_stack.append((current_depth, doc.page_content))
                
            else:
                # 这是一个内容元素 (UncategorizedText, ListItem 等)
                # 构建面包屑路径
                breadcrumbs = " > ".join([h[1] for h in header_stack])
                
                # 策略二：内容拼接 (Context Prepending)
                # 我们创建一个新的字典或对象来表示要存入向量库的数据
                enriched_item = {
                    "original_text": doc.page_content,
                    "context_text": f"{breadcrumbs}: {doc.page_content}" if breadcrumbs else doc.page_content,
                    "metadata": doc.metadata.to_dict(),
                    "breadcrumbs": breadcrumbs
                }
                enriched_data.append(enriched_item)
                
        return enriched_data

    def _split_element(self,document:Document)->Document:
        """
        todo:
        在单个element内，如果内容长度超出最大长度，进行切分
        通过RecursiveCharacterTextSplitter进行切分，暂不实现
        """
        