from services.parsers.base import BaseParser
from typing import List
from langchain_community.document_loaders import CSVLoader

class CSVParser(BaseParser):
    """
    CSV文件解析器
    """

    def parse(self, file_path: str) -> List:
        """
        解析CSV文件内容
        :param file_path: CSV文件路径
        :return: 解析后的文本内容
        """
        loader = CSVLoader(file_path=file_path)
        documents = loader.load()
        return documents