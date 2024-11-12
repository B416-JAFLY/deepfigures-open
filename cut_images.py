import os
import json
from PIL import Image

def process_output_directory(output_dir):
    """遍历输出目录下的每个子目录，处理其中的 .json 文件"""
    for subdir in os.listdir(output_dir):
        subdir_path = os.path.join(output_dir, subdir)
        if os.path.isdir(subdir_path):
            # 遍历子目录中的所有文件，寻找 .json 文件
            for file in os.listdir(subdir_path):
                if file.endswith('.json'):
                    json_file = os.path.join(subdir_path, file)
                    print(f"Processing JSON file: {json_file}")
                    process_json_file(json_file, subdir_path)
                    break  # 处理完第一个找到的 .json 文件后退出
            else:
                print(f"No JSON file found in: {subdir_path}")

def process_json_file(json_file, subdir_path):
    """根据 JSON 文件裁剪图像并保存"""
    if not json_file or not os.path.exists(json_file):
        print(f"JSON file not found: {json_file}")
        return  # 如果没有找到 JSON 文件，则直接返回

    print(f"Processing JSON file: {json_file}")  # 调试信息

    with open(json_file, 'r') as f:
        data = json.load(f)

    # 动态查找 PDF 文件名（无后缀）
    pdf_file_name = find_pdf_file(subdir_path)
    if not pdf_file_name:
        print(f"No PDF file found in {subdir_path}")
        return

    # 构建 DPI 200 图像的基础路径
    images_base_path = os.path.join(subdir_path, f'{pdf_file_name}.pdf-images', 'ghostscript', 'dpi200')

    # 图像保存路径
    images_dir = os.path.join(subdir_path, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # 处理 figures
    for figure in data.get("figures", []):
        process_figure(figure, images_base_path, images_dir, pdf_file_name)

    # 处理 regionless-captions
    for caption in data.get("raw_pdffigures_output", {}).get("regionless-captions", []):
        process_figure(caption, images_base_path, images_dir, pdf_file_name)

def find_pdf_file(subdir_path):
    """根据子目录中的 .pdf 文件动态获取 PDF 文件名（无后缀）"""
    for file in os.listdir(subdir_path):
        if file.endswith('.pdf'):
            return os.path.splitext(file)[0]  # 返回文件名，不带 .pdf 后缀
    return None

def process_figure(figure, images_base_path, images_dir, pdf_file_name):
    """处理单个 figure 或 caption 并裁剪保存"""
    boundary = figure.get('figure_boundary', figure.get('boundary'))
    page_number = figure['page']
    figure_type = figure.get("figure_type", "unknown")
    figure_name = figure.get("name", "unknown")

    # 跳过 figure_type 或 name 为 "unknown" 的情况
    if figure_type == "unknown" or figure_name == "unknown":
        print(f"Skipping figure with unknown type or name: {figure_type}, {figure_name}")
        return

    # 页码加1计算实际图像文件名 (JSON 页码 + 1)
    adjusted_page_number = page_number + 1

    # 构建 DPI 200 图像的文件路径
    image_path = os.path.join(images_base_path, f'{pdf_file_name}.pdf-dpi200-page{adjusted_page_number:04d}.png')

    # 如果图像文件存在，则裁剪并保存
    if os.path.exists(image_path):
        cropped_image_path = os.path.join(images_dir, f'{figure_type}_page{adjusted_page_number:04d}_{figure_type}_{figure_name}.png')
        adjusted_boundary = convert_dpi100_to_dpi200(boundary)  # 将边界从 DPI 100 转换为 DPI 200
        crop_image(image_path, adjusted_boundary, cropped_image_path)
    else:
        print(f"Image file not found: {image_path}")

def convert_dpi100_to_dpi200(boundary):
    """将 dpi100 的坐标转换为 dpi200 的坐标"""
    if boundary:
        return {
            'x1': boundary['x1'] * 2,
            'y1': boundary['y1'] * 2,
            'x2': boundary['x2'] * 2,
            'y2': boundary['y2'] * 2
        }
    return None

def crop_image(image_path, boundary, output_path):
    """裁剪图像并保存"""
    if boundary is None:
        print(f"Invalid boundary for cropping: {boundary}")
        return

    with Image.open(image_path) as im:
        # 裁剪图像
        cropped_image = im.crop((boundary['x1'], boundary['y1'], boundary['x2'], boundary['y2']))
        # 保存裁剪后的图像
        cropped_image.save(output_path)
        print(f"Saved cropped image to {output_path}")

if __name__ == "__main__":
    output_directory = './output'
    process_output_directory(output_directory)