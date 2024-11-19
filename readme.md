### 部署方法

1. **放置 `Scala-pdffigures2`**：
    - [下载地址](https://github.com/B416-JAFLY/deepfigures-open/releases/download/release/pdffigures2-assembly-0.0.12-SNAPSHOT.jar)
    - `Scala-pdffigures2`文件放置路径
        ```bash
        ./workspaces/deepfigures-open/bin/pdffigures2-assembly-0.0.12-SNAPSHOT.jar
        ```

2. **放置 `texlive`：**
    - [下载地址](https://github.com/B416-JAFLY/deepfigures-open/releases/download/release/texlive-fonts-extra.deb)
    - `texlive-fonts-extra.deb` 文件放置路径：
      ```bash
      ./workspaces/deepfigures-open/software/texlive-fonts-extra.deb
      ```

3. **模型权重**：
    - [下载地址](https://github.com/B416-JAFLY/deepfigures-open/releases/download/release/weights.tar.gz)
    - 权重放置路径：
      ```bash
      ./workspaces/deepfigures-open/weights
      ├── save.ckpt-500000.meta
      ├── save.ckpt-500000.index
      ├── save.ckpt-500000.data-00000-of-00001
      └── hypes.json
      ```

4. **依赖安装**：
    - 使用conda管理依赖：
      ```bash
      conda env create -f environment.yml
      conda activate celery
      ```

5. **启动应用**：
    - 服务端
      ```bash
      python app.py
      ```
    - 消息队列
      ```bash
      docker run -p 6379:6379 redis
      ```     
    - 在celery_tasks.py填写服务端与消息队列的地址：
      ```python
      app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
      flask_server_url ='http://localhost:5020/results_upload'
      ```
    - 启动分布式celery worker：
      ```bash
      sudo celery -A celery_tasks worker --loglevel=info
      ```
---
### API 用法

1. **主页接口 `/`**

    - **请求方式**：`GET`
    - **描述**：确认一下服务器是否搭建成功。

    - **返回示例**：
      ```html
      <html>
          <head><title>Welcome to DeepFigures API</title></head>
          <body>
              <h1>Welcome to DeepFigures API</h1>
              <p>This is a simple Flask application for processing PDF files containing figures.</p>
              <p>You can upload a PDF file, and the system will extract images and provide download links.</p>
              <p>To get started, use the /upload endpoint to upload a PDF.</p>
          </body>
      </html>
      ```

2. **文件上传接口 `/upload`**

    - **请求方式**：`POST`
    - **描述**：上传一个 PDF 文件，系统会提取其中的图像，并返回图像的下载链接,以及图像对应的标题的.json文件。
    
    - **请求参数**：
      - `file`：PDF 文件（必填）

    - **返回示例**：
      ```json
      {
        "images": [
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Table_page0003_Table_1.png",
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Figure_page0006_Figure_3.png",
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Figure_page0005_Figure_2.png",
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Figure_page0003_Figure_1.png",
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Table_page0007_Table_2.png",
          "/download/2118e975-1549-4556-bab1-e0a305735f11/Figure_page0008_Figure_4.png"
        ],
        "json": "/download/2118e975-1549-4556-bab1-e0a305735f11/processed_figures.json"
      }
      ```
      

3. **下载图像接口 `/download/<file_id>/<filename>`**

    - **请求方式**：`GET`
    - **描述**：根据文件 ID 和图像文件名提供下载链接。
    
    - **请求参数**：
      - `file_id`：上传 PDF 时生成的唯一 ID
      - `filename`：图片文件名（例如：`figure1.png`）
    
    - **返回示例**：
      - 返回图片文件：图片数据

4. **下载.json文件接口 `/download/<file_id>/processed_figures.json`**

    - **请求方式**：`GET`
    - **描述**：根据文件 ID 提供figure captions下载链接。
    
    - **请求参数**：
      - `file_id`：上传 PDF 时生成的唯一 ID
    
    - **返回示例**：
      ```json
      {"figures": [],
          "regionless-captions": [
              {
                  "figType": "Table",
                  "name": "2",
                  "page": 6,
                  "text": "Table 2: Adsorption and dissociation energies of CO2 and CH4 at metal and interface."
              },
              {
                  "figType": "Table",
                  "name": "1",
                  "page": 2,
                  "text": "Table 1: Chemical compositions and abbreviations of the samples."
              }
          ]
      }
      ```
---

### 批量处理 PDF 文件

#### 批处理脚本

脚本 `pdf_batch_process.py` 批量处理 PDF 文件。

- **功能**：
  1. 重命名文件名中包含空格的 PDF。
  2. 提取 PDF 中的图片和 JSON 数据。

- **运行**：
    ```bash
    python pdf_batch_process.py
    ```

- **输入**：
    - PDF 文件所在的目录路径。
    - 最大线程数（默认为 4）。

- **注意**：
    - 脚本会在同目录生成 `json_` 和 `images_` 开头的文件夹存储提取的数据。

---