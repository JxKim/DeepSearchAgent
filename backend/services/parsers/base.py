from abc import ABC




class BaseParser(ABC):
    """
    文件解析器基类
    """

    def parse(self, file_path: str) -> str:
        """
        解析文件内容
        :param file_path: 文件路径
        :return: 解析后的文本内容
        """
        pass

    
