from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import subprocess
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 文件上传目录
UPLOAD_FOLDER = '/workspaces/deepfigures-open/uploads'
# 处理后的输出目录（deepfigures-open 的输出路径）
OUTPUT_FOLDER = '/workspaces/deepfigures-open/workspaces/deepfigures-open/output'
# 图片最终保存目录
FINAL_OUTPUT_FOLDER = '/workspaces/deepfigures-open/processed_images'

# 配置 Flask 应用的上传和输出路径
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['FINAL_OUTPUT_FOLDER'] = FINAL_OUTPUT_FOLDER

# 创建必要的文件夹（如果不存在则创建）
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['FINAL_OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """
    检查文件的扩展名是否为允许的类型（只允许 PDF 文件）。
    
    :param filename: 上传文件的文件名
    :return: 如果文件是 PDF 格式返回 True，否则返回 False
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def get_first_subdirectory(directory):
    """
    获取指定目录中的第一个子目录。
    
    :param directory: 待查找的父目录
    :return: 第一个子目录的路径，如果没有找到则返回 None
    """
    for subdir in os.listdir(directory):
        subdir_path = os.path.join(directory, subdir)
        if os.path.isdir(subdir_path):
            return subdir_path
    return None

def move_images_to_final_folder(source_dir, dest_dir, file_id):
    """
    将 source_dir 中的 PNG 图片移动到 dest_dir，保存在以 UUID 命名的子目录中。

    :param source_dir: 源目录，包含处理后的图片
    :param dest_dir: 目标目录，保存图片的最终目录
    :param file_id: 用于命名目标目录的 UUID
    :return: 移动的图片文件名列表
    """
    # 创建以 UUID 命名的目标子目录
    target_dir = os.path.join(dest_dir, file_id)
    os.makedirs(target_dir, exist_ok=True)

    # 移动 PNG 图片并返回图片文件名列表
    moved_images = []
    for file in os.listdir(source_dir):
        if file.endswith('.png'):
            source_file = os.path.join(source_dir, file)
            target_file = os.path.join(target_dir, file)
            shutil.move(source_file, target_file)
            moved_images.append(file)
    
    return moved_images

def clear_output_directory(directory):
    """
    清空指定目录中的所有内容。
    
    :param directory: 需要清空的目录
    """
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        elif os.path.isfile(item_path):
            os.remove(item_path)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    """
    处理 PDF 文件上传的 API 端点。
    
    1. 检查是否有文件上传。
    2. 检查文件是否是 PDF 格式。
    3. 保存文件到 uploads 目录。
    4. 使用 `python manage.py detectfigures` 处理 PDF。
    5. 使用 `cut_images.py` 进一步处理生成的图片。
    6. 返回生成的图片 URL 列表给前端。
    
    :return: JSON 响应，包含生成的图片列表或错误信息。
    """
    # 检查请求中是否有文件
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    # 获取上传的文件
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 检查文件是否符合要求（是否为 PDF）
    if file and allowed_file(file.filename):
        # 使用 `secure_filename` 确保文件名安全
        filename = secure_filename(file.filename)
        # 为文件生成一个唯一的 ID，避免文件名冲突
        file_id = str(uuid.uuid4())
        # 保存文件到 uploads 文件夹，文件名为 UUID.pdf
        pdf_save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.pdf")
        file.save(pdf_save_path)

        # Step 2: 调用 `manage.py detectfigures` 处理 PDF 文件
        try:
            # 构建命令行参数，调用 detectfigures
            detectfigures_command = [
                'python', 'manage.py', 'detectfigures',
                app.config['OUTPUT_FOLDER'], pdf_save_path
            ]
            # 使用 subprocess 调用命令，指定工作目录为 `deepfigures-open`
            subprocess.run(detectfigures_command, check=True, cwd='./workspaces/deepfigures-open')

        except subprocess.CalledProcessError as e:
            # 如果命令执行失败，返回错误信息
            return jsonify({"error": f"Failed to run detectfigures: {str(e)}"}), 500

        # Step 3: 调用 `cut_images.py` 进一步处理生成的图片
        try:
            # 构建命令行参数，使用 `sudo` 调用 `cut_images.py`
            cut_images_command = ['sudo', 'python', 'cut_images.py']
            
            # 使用 subprocess 调用命令，指定工作目录为 `deepfigures-open`
            subprocess.run(cut_images_command, check=True, cwd='./workspaces/deepfigures-open')
        except subprocess.CalledProcessError as e:
            # 如果命令执行失败，返回错误信息
            return jsonify({"error": f"Failed to run cut_images: {str(e)}"}), 500

        # Step 4: 查找生成的图片并返回前端
        # 获取 "output" 目录下的第一个子目录（处理结果所在路径）
        first_subdir = get_first_subdirectory(app.config['OUTPUT_FOLDER'])
        if not first_subdir:
            return jsonify({"error": "No output directory found after processing"}), 404

        # 检查第一个子目录中的 "images" 子目录是否存在
        images_dir = os.path.join(first_subdir, 'images')
        if not os.path.exists(images_dir):
            return jsonify({"error": "No images directory found in output"}), 404

        # Step 5: 移动图片到最终保存目录
        moved_images = move_images_to_final_folder(images_dir, app.config['FINAL_OUTPUT_FOLDER'], file_id)

        # Step 6: 清理 output 目录
        clear_output_directory(app.config['OUTPUT_FOLDER'])

        # 构建图片的下载 URL 列表，供前端使用
        image_urls = [f"/download/{file_id}/{img}" for img in moved_images]

        # 返回图片列表作为 JSON 响应
        return jsonify({"images": image_urls}), 200

    # 如果文件类型不允许，返回错误信息
    return jsonify({"error": "Invalid file type. Only PDF is allowed."}), 400

@app.route('/download/<file_id>/<filename>', methods=['GET'])
def download_image(file_id, filename):
    """
    提供下载处理后图像的 API 端点。
    
    根据文件 ID 和文件名返回处理后的 PNG 图片。
    
    :param file_id: 文件的唯一 ID
    :param filename: 图片文件名
    :return: 图片文件或错误信息
    """
    # 构建图片的存储路径
    target_dir = os.path.join(app.config['FINAL_OUTPUT_FOLDER'], file_id)
    
    # 检查图片文件是否存在
    if os.path.exists(os.path.join(target_dir, filename)):
        # 使用 Flask 的 `send_from_directory` 函数发送文件
        return send_from_directory(target_dir, filename)
    else:
        # 如果文件不存在，返回 404 错误
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    # 启动 Flask 应用，开启调试模式
    app.run(debug=True)