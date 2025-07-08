# SciTiger 视频编辑服务

视频编辑服务是 SciTiger AI模型调用微服务体系的一部分，提供视频剪辑、滤镜效果、转场效果等功能，通过统一的API接口进行调用。

## 功能特性

- 支持多种视频编辑操作
- 视频剪辑：裁剪、分割、合并、速度调整、倒放
- 视频滤镜：亮度、对比度、饱和度、模糊、锐化等
- 视频转场：淡入淡出、溶解、擦除、滑动等
- 自动剪辑：基于音乐节奏的视频自动剪辑、智能剪辑、精彩片段剪辑
- 异步任务处理
- 任务状态跟踪和结果获取
- 统一的API接口
- 集成认证系统

## 支持的操作

### 视频剪辑处理器 (clip)

- trim：裁剪视频片段
- split：分割视频
- merge：合并多个视频
- speed：调整视频速度
- reverse：视频倒放

### 视频滤镜处理器 (filter)

- brightness：亮度调整
- contrast：对比度调整
- saturation：饱和度调整
- blur：模糊效果
- sharpen：锐化效果
- grayscale：灰度效果
- sepia：复古效果
- vignette：暗角效果

### 视频转场处理器 (transition)

- fade：淡入淡出
- dissolve：溶解
- wipe：擦除
- slide：滑动
- zoom：缩放
- rotate：旋转
- flash：闪烁
- crossfade：交叉淡化

### 自动剪辑处理器 (auto)

- music_edit：基于音乐的自动剪辑
- smart_edit：智能剪辑
- highlight_edit：精彩片段剪辑

## 实现说明

本服务使用异步方式处理视频编辑任务。流程如下：

1. 服务接收用户请求并创建任务记录
2. 使用异步方式调用相应处理器进行视频处理
3. 处理完成后更新任务状态和结果
4. 返回处理结果给用户，包括处理后的视频路径

### 视频存储

- 处理后的视频会保存到 `data/videos` 目录
- 文件名格式：`{处理器}_{操作}_{时间戳}_{随机ID}.mp4`
- 任务结果中会包含视频的本地保存路径

## 快速开始

### 环境准备

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 安装FFmpeg

本服务依赖FFmpeg进行视频处理，请确保系统中已安装FFmpeg。

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载FFmpeg并添加到系统PATH
```

3. 配置环境变量

复制`.env.example`为`.env`，并根据实际情况修改配置：

```bash
cp .env.example .env
```

主要配置项：

- `MONGODB_URL`：MongoDB连接地址
- `REDIS_URL`：Redis连接地址（用于Celery）
- `FFMPEG_PATH`：FFmpeg可执行文件路径（如果不在系统PATH中）
- `DATA_DIR`：数据存储目录

### 启动服务

1. 启动API服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

2. 启动Celery Worker

```bash
celery -A app.core.celery_app worker --loglevel=info
```

## API使用

### 上传文件接口

#### 单文件上传

```
POST /api/v1/upload/
```

请求参数：
- `file`：要上传的文件（表单字段）
- `category`：文件分类（可选，如不提供将自动判断）

响应示例：
```json
{
  "success": true,
  "message": "文件上传成功",
  "data": {
    "filename": "20240620_123456_a1b2c3d4.mp4",
    "original_filename": "my_video.mp4",
    "size": 1024000,
    "content_type": "video/mp4",
    "category": "videos",
    "media_url": "/media/videos/20240620_123456_a1b2c3d4.mp4",
    "full_url": "http://127.0.0.1:8084/media/videos/20240620_123456_a1b2c3d4.mp4",
    "download_url": "http://127.0.0.1:8084/api/v1/download/20240620_123456_a1b2c3d4.mp4"
  }
}
```

**文件类别自动判断**：
- 如果不提供`category`参数，系统将根据文件类型自动判断适合的分类
- 图片文件（jpg, png, gif等）→ `images`
- 视频文件（mp4, avi, mov等）→ `videos`
- 音频文件（mp3, wav等）→ `audio`
- 文档文件（pdf, doc, txt等）→ `documents`
- 无法判断的文件 → `general`

#### 批量文件上传

```
POST /api/v1/upload/batch
```

请求参数：
- `files`：要上传的文件列表（表单字段）
- `category`：文件分类（可选，如不提供将对每个文件自动判断）

响应示例：
```json
{
  "success": true,
  "message": "成功上传 2 个文件",
  "data": [
    {
      "filename": "20240620_123456_a1b2c3d4.mp4",
      "original_filename": "video1.mp4",
      "size": 1024000,
      "content_type": "video/mp4",
      "category": "videos",
      "media_url": "/media/videos/20240620_123456_a1b2c3d4.mp4",
      "full_url": "http://127.0.0.1:8084/media/videos/20240620_123456_a1b2c3d4.mp4",
      "download_url": "http://127.0.0.1:8084/api/v1/download/20240620_123456_a1b2c3d4.mp4"
    },
    {
      "filename": "20240620_123500_e5f6g7h8.mp4",
      "original_filename": "video2.mp4",
      "size": 2048000,
      "content_type": "video/mp4",
      "category": "videos",
      "media_url": "/media/videos/20240620_123500_e5f6g7h8.mp4",
      "full_url": "http://127.0.0.1:8084/media/videos/20240620_123500_e5f6g7h8.mp4",
      "download_url": "http://127.0.0.1:8084/api/v1/download/20240620_123500_e5f6g7h8.mp4"
    }
  ]
}
```

### 创建视频剪辑任务

#### 视频剪辑处理器 (clip)

##### 裁剪视频 (trim)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "trim",
    "processor": "clip",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "start_time": 10.5,
      "end_time": 30.2,
      "copy_codec": false
    },
    "is_async": true
  }'
```

##### 分割视频 (split)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "split",
    "processor": "clip",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "split_points": [30, 60, 90],
      "copy_codec": false
    },
    "is_async": true
  }'
```

##### 合并视频 (merge)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "merge",
    "processor": "clip",
    "parameters": {
      "video_paths": [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4"
      ],
      "transition": null
    },
    "is_async": true
  }'
```

##### 调整视频速度 (speed)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "speed",
    "processor": "clip",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "speed_factor": 1.5
    },
    "is_async": true
  }'
```

##### 视频倒放 (reverse)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "reverse",
    "processor": "clip",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "with_audio": false
    },
    "is_async": true
  }'
```

#### 视频滤镜处理器 (filter)

##### 亮度调整 (brightness)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "brightness",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "level": 20
    },
    "is_async": true
  }'
```

##### 对比度调整 (contrast)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "contrast",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "level": 15
    },
    "is_async": true
  }'
```

##### 饱和度调整 (saturation)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "saturation",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "level": 30
    },
    "is_async": true
  }'
```

##### 模糊效果 (blur)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "blur",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "radius": 5
    },
    "is_async": true
  }'
```

##### 锐化效果 (sharpen)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "sharpen",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "amount": 1.5
    },
    "is_async": true
  }'
```

##### 灰度效果 (grayscale)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "grayscale",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4"
    },
    "is_async": true
  }'
```

##### 复古效果 (sepia)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "sepia",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4"
    },
    "is_async": true
  }'
```

##### 暗角效果 (vignette)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "vignette",
    "processor": "filter",
    "parameters": {
      "video_path": "/path/to/source/video.mp4",
      "amount": 0.3
    },
    "is_async": true
  }'
```

#### 视频转场处理器 (transition)

##### 淡入淡出 (fade)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "fade",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "duration": 2.0
    },
    "is_async": true
  }'
```

##### 溶解 (dissolve)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "dissolve",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "duration": 1.5
    },
    "is_async": true
  }'
```

##### 擦除 (wipe)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "wipe",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "direction": "left-to-right",
      "duration": 1.0
    },
    "is_async": true
  }'
```

##### 滑动 (slide)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "slide",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "direction": "left",
      "duration": 1.0
    },
    "is_async": true
  }'
```

##### 缩放 (zoom)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "zoom",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "direction": "in",
      "duration": 1.5
    },
    "is_async": true
  }'
```

##### 旋转 (rotate)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "rotate",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "direction": "clockwise",
      "duration": 1.2
    },
    "is_async": true
  }'
```

##### 闪烁 (flash)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "flash",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "intensity": 1.0,
      "duration": 0.5
    },
    "is_async": true
  }'
```

##### 交叉淡化 (crossfade)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "crossfade",
    "processor": "transition",
    "parameters": {
      "video1_path": "/path/to/source/video1.mp4",
      "video2_path": "/path/to/source/video2.mp4",
      "duration": 2.0
    },
    "is_async": true
  }'
```

#### 自动剪辑处理器 (auto)

##### 基于音乐的自动剪辑 (music_edit)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "music_edit",
    "processor": "auto",
    "parameters": {
      "video_paths": [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4"
      ],
      "music_path": "/path/to/music.mp3",
      "strategy": "rhythm",
      "transition_type": "fade",
      "transition_duration": 0.5
    },
    "is_async": true
  }'
```

支持的策略（strategy）：
- rhythm：根据音乐节奏点分配视频片段
- energy：根据音乐能量分配视频片段
- even：均匀分配视频片段

##### 智能剪辑 (smart_edit)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "smart_edit",
    "processor": "auto",
    "parameters": {
      "video_paths": [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4"
      ],
      "target_duration": 30.0,
      "music_path": "/path/to/music.mp3",
      "transition_type": "fade",
      "transition_duration": 0.5
    },
    "is_async": true
  }'
```

##### 精彩片段剪辑 (highlight_edit)

```bash
curl -X POST "http://localhost:8003/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "highlight_edit",
    "processor": "auto",
    "parameters": {
      "video_paths": [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4"
      ],
      "highlight_count": 5,
      "clip_duration": 3.0,
      "music_path": "/path/to/music.mp3",
      "transition_type": "fade",
      "transition_duration": 0.5
    },
    "is_async": true
  }'
```

### 查询任务状态

```bash
curl "http://localhost:8003/api/v1/tasks/{task_id}/status"
```

### 获取任务结果

```bash
curl "http://localhost:8003/api/v1/tasks/{task_id}/result"
```

任务结果示例：

```json
{
  "success": true,
  "message": "获取任务结果成功",
  "results": {
    "task_id": "685008a3404376ca4660b24a",
    "status": "completed",
    "result": {
      "status": "success",
      "operation": "trim",
      "output_path": "/path/to/trimmed_video_10.5_30.2.mp4",
      "duration": 19.7
    },
    "error": null
  }
}
```

## 开发指南

### 项目结构

```
video-edit-service/
├── app/                           # 应用主目录
│   ├── api/                       # API路由定义
│   │   ├── __init__.py            # API路由注册
│   │   ├── health.py              # 健康检查接口
│   │   └── tasks.py               # 任务管理接口
│   ├── core/                      # 核心功能模块
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── security.py            # 安全和认证
│   │   ├── celery_app.py          # Celery应用实例
│   │   └── logging.py             # 日志配置
│   ├── db/                        # 数据库相关
│   │   ├── __init__.py
│   │   ├── mongodb.py             # MongoDB连接和操作
│   │   └── repositories/          # 数据访问层
│   │       ├── __init__.py
│   │       └── task_repository.py # 任务数据访问
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── task.py                # 任务模型
│   │   └── user.py                # 用户模型
│   ├── schemas/                   # Pydantic模式
│   │   ├── __init__.py
│   │   ├── task.py                # 任务相关模式
│   │   └── common.py              # 通用模式
│   ├── services/                  # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── task_service.py        # 任务管理服务
│   │   └── edit_processors/       # 视频处理器实现
│   │       ├── __init__.py
│   │       ├── base.py            # 基础接口
│   │       ├── clip_processor.py  # 剪辑处理器
│   │       ├── filter_processor.py # 滤镜处理器
│   │       ├── transition_processor.py # 转场处理器
│   │       └── auto_processor.py  # 自动剪辑处理器
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── helpers.py             # 辅助函数
│   │   ├── response.py            # 统一响应格式
│   │   ├── video_utils.py         # 视频处理工具
│   │   ├── music_utils.py         # 音乐处理工具
│   │   └── auto_edit_utils.py     # 自动剪辑工具
│   ├── worker/                    # 后台任务处理
│   │   ├── __init__.py
│   │   └── tasks.py               # Celery任务定义
│   ├── middleware/                # 中间件
│   │   ├── __init__.py
│   │   └── auth.py                # 认证中间件
│   └── main.py                    # 应用入口
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git忽略文件
├── requirements.txt               # 依赖列表
└── README.md                      # 项目说明
```

### 添加新的视频处理器

要添加新的视频处理器，请执行以下步骤：

1. 在 `app/services/edit_processors` 目录中创建新的处理器类
2. 实现 `EditProcessor` 抽象类定义的接口
3. 在 `app/services/edit_processors/__init__.py` 中导入和注册新的处理器

示例：

```python
# app/services/edit_processors/new_processor.py
from typing import Dict, Any, List
from . import register_processor
from .base import EditProcessor

@register_processor
class NewProcessor(EditProcessor):
    @property
    def processor_name(self) -> str:
        return "new_processor"
    
    @property
    def supported_operations(self) -> List[str]:
        return ["operation1", "operation2"]
    
    async def process_video(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 实现视频处理逻辑
        pass
    
    async def validate_parameters(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 实现参数验证逻辑
        pass
```

然后在 `app/services/edit_processors/__init__.py` 中添加导入：

```python
# 添加到文件末尾
from . import new_processor  # 新处理器
```

