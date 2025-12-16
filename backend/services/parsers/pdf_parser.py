from services.parsers.base import BaseParser
from typing import List
from langchain_community.document_loaders import UnstructuredPDFLoader
from config.loader import get_config

config = get_config()


class PDFParser(BaseParser):
    """
    PDF文件解析器
    """

    def parse(self, file_path: str) -> List:
        """
        解析PDF文件内容
        :param file_path: PDF文件路径
        :return: 解析后的文本内容
        """
        elements = UnstructuredPDFLoader(file_path=file_path,
        mode="elements",
        strategy="hi_res",infer_table_structure=True,languages=["eng","chi_sim"]).load()
        # elements = partition_pdf(file_path)
        return elements

class MineruPDFLoader(BaseParser):
    """
    使用Mineru解析PDF文件
    本地部署Mineru，解决数据安全性问题
    """

    async def upload_file(self,file_path:str):
        """
        上传文件至Mineru
        """
        pass



    def parse(self, file_path: str) -> List:
        """
        解析PDF文件内容
        :param file_path: PDF文件路径
        :return: 解析后的文本内容
        """
        pass


class LLAMaIndexPDFParser(PDFParser):
    """
    使用LLAMaIndex解析PDF文件，需要使用到LLamaCloud。对于数据安全有一定的影响
    """

