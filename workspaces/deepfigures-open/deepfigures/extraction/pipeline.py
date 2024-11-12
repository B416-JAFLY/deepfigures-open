import hashlib  # 用于生成PDF文件的哈希值
import os  # 提供操作系统依赖的功能，如文件路径管理
import shutil  # 提供文件操作，如复制、移动文件

from PIL import Image  # 用于处理图像操作

from deepfigures import settings  # deepfigures模块的设置
from deepfigures.extraction import (
    detection,  # 用于图像检测的模块
    pdffigures_wrapper,  # 用于调用pdffigures2的模块
    renderers)  # 用于渲染PDF为图像的模块
from deepfigures.utils import (
    misc,  # 提供杂项功能，如哈希计算
    settings_utils)  # 提供与设置相关的实用程序函数


class FigureExtraction(object):
    """一个表示从PDF中提取的数据的类。

    ``FigureExtraction`` 类表示从单个PDF中提取的数据，
    并通过 ``FigureExtractionPipeline`` 类的 ``extract`` 方法生成。

    Attributes
    ----------
    path_templates : Dict[str, str]
        提取数据在磁盘上的路径模板，使用PDF的哈希值生成目录结构。
    paths : Dict[str, str]
        一个字典，将路径名称映射到其在磁盘上的实际绝对路径。
    parent_directory : str
        存储提取数据的父目录。
    low_res_rendering_paths : Optional[str]
        PDF的低分辨率渲染图像路径（用于预测边界框）。
    hi_res_rendering_paths : Optional[str]
        PDF的高分辨率渲染图像路径（用于裁剪出图像）。
    pdffigures_output_path : Optional[str]
        运行 pdffigures2 的输出路径。
    deepfigures_json_path : Optional[str]
        deepfigures 生成的预测边界框的JSON文件路径。
    """

    # 定义路径模板，使用哈希值作为目录名，其他路径基于此生成
    path_templates = {
        'BASE': '{pdf_hash}',  # 根目录，使用PDF的哈希值作为目录名
        'PDF_PATH': '{base}/{pdf_name}',  # 存储PDF文件的路径
        'RENDERINGS_PATH': '{base}/page-renderings',  # 存储渲染图像的路径
        'PDFFIGURES_OUTPUT_PATH': '{base}/pdffigures-output',  # pdffigures的输出路径
        'DEEPFIGURES_OUTPUT_PATH': '{base}/deepfigures-output',  # deepfigures的输出路径
        'FIGURE_IMAGES_PATH': '{base}/figure-images'  # 存储裁剪出的图像的路径
    }

    def __init__(self, pdf_path, parent_directory):
        """初始化 ``FigureExtraction`` 实例。

        Parameters
        ----------
        pdf_path : str
            本地磁盘上PDF的路径。
        parent_directory : str
            用于存储提取结果的父目录。
        """
        # 计算PDF文件的哈希值，用于唯一标识该PDF文件
        pdf_hash = misc.hash_out_of_core(hashlib.sha1, pdf_path)
        # 提取PDF文件的名称（不包含路径）
        pdf_name = os.path.basename(pdf_path)
        # 生成基础目录名，使用哈希值替换路径模板中的变量
        base = self.path_templates['BASE'].format(pdf_hash=pdf_hash)
        # 创建一个包含模板变量的字典，用于填充其他路径模板
        template_vars = {
            'pdf_hash': pdf_hash,  # 哈希值
            'pdf_name': pdf_name,  # PDF文件名
            'base': base  # 基础目录名
        }
        # 使用模板变量填充路径模板，生成各个路径并存储到 `paths` 字典中
        self.paths = {
            k: os.path.join(parent_directory, v.format(**template_vars))
            for k, v in self.path_templates.items()
        }
        # 保存父目录路径
        self.parent_directory = parent_directory
        # 初始化低分辨率渲染路径为空，稍后会填充
        self.low_res_rendering_paths = None
        # 初始化高分辨率渲染路径为空，稍后会填充
        self.hi_res_rendering_paths = None
        # 初始化 pdffigures 输出路径为空，稍后会填充
        self.pdf_figures_output_path = None
        # 初始化 deepfigures JSON 输出路径为空，稍后会填充
        self.deepfigures_json_path = None


class FigureExtractionPipeline(object):
    """用于从PDF中提取图像数据的类。

    ``FigureExtractionPipeline`` 类的主要功能是生成 
    ``FigureExtraction`` 实例，用于存储提取的PDF数据。

    """

    def extract(self, pdf_path, output_directory):
        """为 ``pdf_path`` 返回一个 ``FigureExtraction`` 实例。

        从 ``pdf_path`` 所指的PDF中提取图像和相关信息，
        将结果保存到 ``output_directory`` 目录中，并返回相应的
        ``FigureExtraction`` 实例。

        Parameters
        ----------
        pdf_path : str
            PDF的路径。
        output_directory : str
            保存提取结果的目录。

        Returns
        -------
        FigureExtraction
            代表该PDF的 ``FigureExtraction`` 实例。
        """
        # 创建FigureExtraction实例，用于管理提取的文件和路径
        figure_extraction = FigureExtraction(
            pdf_path=pdf_path,  # PDF文件路径
            parent_directory=output_directory  # 提取结果的父目录
        )

        # 创建基础目录，用于保存提取的文件（如PDF、渲染图像等）
        os.makedirs(figure_extraction.paths['BASE'], exist_ok=True)

        # 将PDF文件复制到提取结果目录中
        shutil.copy(pdf_path, figure_extraction.paths['PDF_PATH'])

        # 导入并初始化PDF渲染器，用于将PDF页面渲染为图像
        pdf_renderer = settings_utils.import_setting(
            settings.DEEPFIGURES_PDF_RENDERER)()

        # 渲染低分辨率的PDF页面图像，适用于边界框预测
        figure_extraction.low_res_rendering_paths = \
            pdf_renderer.render(
                pdf_path=figure_extraction.paths['PDF_PATH'],  # PDF文件路径
                output_dir=figure_extraction.paths['BASE'],  # 输出渲染图像的目录
                dpi=settings.DEFAULT_INFERENCE_DPI  # 渲染图像的分辨率
            )

        # 渲染高分辨率的PDF页面图像，适用于图像裁剪
        figure_extraction.hi_res_rendering_paths = \
            pdf_renderer.render(
                pdf_path=figure_extraction.paths['PDF_PATH'],  # PDF文件路径
                output_dir=figure_extraction.paths['BASE'],  # 输出渲染图像的目录
                dpi=settings.DEFAULT_CROPPED_IMG_DPI  # 渲染图像的分辨率
            )

        # 使用pdffigures2工具提取PDF中的图像标题和位置
        figure_extraction.pdffigures_output_path = \
            pdffigures_wrapper.pdffigures_extractor.extract(
                pdf_path=figure_extraction.paths['PDF_PATH'],  # PDF文件路径
                output_dir=figure_extraction.paths['BASE']  # pdffigures 输出目录
            )

        # 使用deepfigures神经网络模型预测PDF图像中的边界框
        figure_extraction.deepfigures_json_path = \
            detection.extract_figures_json(
                pdf_path=figure_extraction.paths['PDF_PATH'],  # PDF文件路径
                page_image_paths=figure_extraction.low_res_rendering_paths,  # 低分辨率图像路径
                pdffigures_output=figure_extraction.pdffigures_output_path,  # pdffigures的输出
                output_directory=figure_extraction.paths['BASE']  # deepfigures输出目录
            )

        # 返回包含提取数据的FigureExtraction实例
        return figure_extraction


# 预期返回的数据结构
# 当调用FigureExtractionPipeline类的extract函数时，它会返回一个FigureExtraction实例。
# 这个实例包含以下数据结构：
#
# FigureExtraction:
# - paths: dict, 包含以下键值对：
#   - 'BASE': 提取结果的根目录（基于PDF的哈希生成）
#   - 'PDF_PATH': 保存PDF文件的路径
#   - 'RENDERINGS_PATH': 保存低分辨率和高分辨率渲染图像的路径
#   - 'PDFFIGURES_OUTPUT_PATH': pdffigures的输出路径
#   - 'DEEPFIGURES_OUTPUT_PATH': deepfigures的输出路径
#   - 'FIGURE_IMAGES_PATH': 保存裁剪出的图像的路径
# - low_res_rendering_paths: list, 低分辨率渲染图像的文件路径列表
# - hi_res_rendering_paths: list, 高分辨率渲染图像的文件路径列表
# - pdffigures_output_path: str, pdffigures工具输出的结果路径
# - deepfigures_json_path: str, deepfigures神经网络生成的JSON文件路径