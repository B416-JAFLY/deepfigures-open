import os
import json
from PIL import Image
import pwd
import grp

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
                    # 处理权限问题
                    ensure_file_accessible(json_file)
                    process_json_file(json_file, subdir_path)
                    break  # 处理完第一个找到的 .json 文件后退出
            else:
                print(f"No JSON file found in: {subdir_path}")

def ensure_file_accessible(file_path):
    """
    确保文件对当前用户可访问。如果需要，修改文件的所有权。
    
    :param file_path: 需要更改权限的文件路径
    """
    try:
        # 获取当前用户的 UID 和 GID
        current_uid = os.geteuid()  # 获取当前用户的 UID
        current_gid = os.getegid()  # 获取当前用户的 GID

        # 获取文件的当前所有权
        file_stat = os.stat(file_path)
        file_uid = file_stat.st_uid
        file_gid = file_stat.st_gid

        # 如果文件不属于当前用户，则尝试更改文件所有权
        if file_uid != current_uid or file_gid != current_gid:
            print(f"Changing ownership of {file_path} to current user ({current_uid}:{current_gid})")
            os.chown(file_path, current_uid, current_gid)
        else:
            print(f"File {file_path} already accessible by the current user.")
    
    except PermissionError as e:
        print(f"Permission denied while changing ownership of {file_path}: {e}")
    except Exception as e:
        print(f"Error occurred while changing ownership of {file_path}: {e}")

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

def set_directory_permissions(directory_path):
    """将目录及其所有子目录和文件的权限递归设置为 777"""
    try:
        # 遍历目录及子目录
        for root, dirs, files in os.walk(directory_path):
            # 设置当前目录的权限为 777
            os.chmod(root, 0o777)
            print(f"Permissions for directory {root} set to 777.")
            
            # 设置所有子文件的权限为 777
            for file in files:
                file_path = os.path.join(root, file)
                os.chmod(file_path, 0o777)
                print(f"Permissions for file {file_path} set to 777.")
    
    except PermissionError as e:
        print(f"Permission denied while changing permissions for {directory_path}: {e}")
    except Exception as e:
        print(f"Error occurred while changing permissions for {directory_path}: {e}")


if __name__ == "__main__":
    output_directory = './output'
    process_output_directory(output_directory)
    
    # 执行完处理后修改输出目录权限为777
    set_directory_permissions(output_directory)
