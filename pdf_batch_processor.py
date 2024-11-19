import os
import glob
import requests
import json
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import shutil
import time

BASE_URL = os.getenv('FLASK_BASE_URL', 'http://192.168.1.110:5020')

MAX_RETRIES = 3  # 最大重试次数

def clear_environment(pdf_path: str):
    """清理与 PDF 文件相关的文件夹"""
    pdf_name = os.path.basename(pdf_path).split(".")[0]
    json_dir = f"json_{pdf_name}"
    img_dir = f"images_{pdf_name}"
    for dir_path in [json_dir, img_dir]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"清理文件夹: {dir_path}")

def download_json(file_id: str, pdf_path: str) -> str:
    pdf_name = os.path.basename(pdf_path).split(".")[0]
    json_dir = f"json_{pdf_name}"
    os.makedirs(json_dir, exist_ok=True)

    try:
        json_url = f"{BASE_URL}/download/{file_id}/processed_figures.json"
        response = requests.get(json_url)
        response.raise_for_status()
        data = response.json()
        json_file_path = os.path.join(json_dir, f"{file_id}_processed_figures.json")
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        print(f"JSON 文件已保存到 {json_file_path}")
        return json_file_path
    except requests.RequestException as e:
        print(f"下载 JSON 数据失败: {e}")
        raise
    except Exception as e:
        print(f"保存 JSON 文件失败: {e}")
        raise

def process_pdf_with_flask(pdf_path: str) -> list:
    url = f"{BASE_URL}/upload"
    files = {'file': open(pdf_path, 'rb')}
    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        json_response = response.json()
        if 'images' in json_response:
            image_urls = json_response['images']
            file_id = json_response.get('file_id', os.path.basename(pdf_path).split('.')[0])
            download_json(file_id, pdf_path)
            return download_images(image_urls, pdf_path)
        else:
            print(f"Error: {json_response.get('error', 'Unknown error occurred')}")
            raise Exception(f"Flask 返回错误信息: {json_response.get('error', 'Unknown error occurred')}")
    except requests.RequestException as e:
        print(f"Failed to process PDF with Flask: {e}")
        raise
    finally:
        files['file'].close()

def download_images(image_urls: list, pdf_path: str) -> list:
    pdf_name = os.path.basename(pdf_path).split(".")[0]
    img_dir = f"images_{pdf_name}"
    os.makedirs(img_dir, exist_ok=True)
    img_list = []
    for i, img_url in enumerate(image_urls):
        try:
            if img_url.startswith('/'):
                img_url = BASE_URL + img_url
            img_response = requests.get(img_url)
            img_response.raise_for_status()
            img = Image.open(BytesIO(img_response.content))
            url_path = urlparse(img_url).path
            file_name = os.path.basename(url_path)
            name_without_extension, file_extension = os.path.splitext(file_name)
            img_extension = img.format.lower()
            if not file_extension:
                file_name = f"{name_without_extension}.{img_extension}"
            else:
                file_name = name_without_extension + file_extension
            file_path = os.path.join(img_dir, file_name)
            img.save(file_path)
            img_list.append(file_path)
        except requests.RequestException as e:
            print(f"Failed to download image {img_url}: {e}")
            raise
        except IOError as e:
            print(f"Failed to save image {img_url}: {e}")
            raise
    return img_list

def process_pdf_with_retry(pdf_path: str):
    """带重试机制的 PDF 处理"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"正在处理 PDF 文件: {pdf_path} (第 {attempt} 次尝试)")
            process_pdf_with_flask(pdf_path)
            print(f"处理完成: {pdf_path}")
            return
        except Exception as e:
            print(f"处理失败: {pdf_path} (第 {attempt} 次尝试)")
            clear_environment(pdf_path)  # 清理环境
            if attempt < MAX_RETRIES:
                print("等待重试...")
                time.sleep(2)  # 等待一段时间再重试
            else:
                print(f"已达到最大重试次数，放弃处理: {pdf_path}")

def process_all_pdfs_in_directory(directory: str, max_workers: int = 4):
    pdf_files = glob.glob(os.path.join(directory, "*.pdf"))
    if not pdf_files:
        print("目录中没有找到 PDF 文件。")
        return

    # 使用多线程池处理所有 PDF 文件
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_pdf_with_retry, pdf_files)

if __name__ == "__main__":
    directory = input("请输入包含 PDF 文件的目录路径: ").strip()
    if os.path.isdir(directory):
        max_threads = input("请输入最大线程数（默认4）: ").strip()
        max_threads = int(max_threads) if max_threads.isdigit() else 4
        process_all_pdfs_in_directory(directory, max_workers=max_threads)
    else:
        print("输入的路径不是有效目录，请重新输入。")
