# KanTu

基于 Git 思路的图库管理工具，使用增量编码实现存储优化。

## 项目背景

KanTu 是一款创新的图库管理工具，其设计灵感来源于 Git 版本控制的核心概念。在现代数字摄影和图像编辑工作流程中，用户经常会积累大量相似图片——编辑版本、裁剪版本、不同曝光或细微变体。传统存储方法将每张图片保存为独立文件，导致显著的存储冗余。KanTu 通过实现增量编码来解决这一挑战：存储一张"基础"图片，并为相似图片仅记录差异（增量），在保持完整图片质量和可访问性的同时，大幅减少存储需求。

"KanTu"（看图）这个名字反映了工具专注于实用图像管理的特点。系统使用感知哈希（pHash）识别相似图片，SSIM（结构相似性指数）判断增量存储是否有益，以及高效的像素级增量编码来最小化存储。每个目录维护自己的图库数据库，实现不同图片集的独立管理。

## 应用场景

KanTu 专为摄影师、设计师以及管理大量相似图片的用户设计。主要用例包括：

1. **摄影工作流程**：以最小存储开销存储多次曝光、编辑版本和变体。一位拥有 5000+ 张图片（包括许多相似照片）的婚礼摄影师可以节省 30-60% 的存储空间。

2. **设计版本控制**：平面设计师经常创建同一设计的多个迭代版本。KanTu 高效存储设计的演进历史，同时保持导出任何版本的能力。

3. **截图归档**：技术文档经常涉及许多相似的截图。增量编码大幅减少这些近乎重复图片的存储需求。

4. **个人照片库**：家庭照片通常包含连拍和编辑版本。KanTu 自动检测并优化这些图片，同时保持所有图片可访问。

5. **Web 应用后端**：REST API 支持集成到 Web 应用程序，实现基于云端的优化存储图库。

## 兼容硬件

KanTu 设计运行于标准消费级硬件，需求适中：

- **CPU**：任何现代处理器（Intel Core i3/AMD Ryzen 3 或更高）。图片哈希和增量计算支持多线程，但对典型图片大小来说并非 CPU 密集型。

- **内存**：最低 4GB RAM，推荐 8GB。图片处理会临时将图片加载到内存，因此更大的图片或批量操作受益于更多内存。

- **GPU**：不需要。所有处理均基于 CPU，使 KanTu 兼容无独立显卡的系统。

- **存储**：增量文件以压缩的 NumPy 数组存储，对相似图片集通常可实现 30-70% 的存储节省。SSD 存储可提升大型图库的数据库性能。

- **显示**：GUI 使用时，任何支持 1024x768 或更高分辨率的显示器。Web 界面响应式设计，适用于各种屏幕尺寸。

## 操作系统

KanTu 跨平台支持，已测试于：

- **Windows**：Windows 10/11，Python 3.9+。PySide6 GUI 与 Windows 样式原生集成。

- **macOS**：macOS 10.15 (Catalina) 或更高版本，Python 3.9+。原生窗口样式和 Retina 显示支持。

- **Linux**：任何现代发行版，Python 3.9+ 和 Qt 库。已测试于 Ubuntu 22.04、Fedora 38 和 Arch Linux。

CLI 界面在所有平台上工作一致。GUI 使用原生窗口装饰并与系统主题集成。Web 界面可在任何现代浏览器（Chrome、Firefox、Safari、Edge）中运行。

## 依赖环境

KanTu 需要 Python 3.9 或更高版本。核心依赖包括：

- **Pillow (10.0+)**：图片 I/O 和基本操作
- **imagehash (4.3+)**：用于相似性检测的感知哈希
- **scikit-image (0.21+)**：SSIM 计算，用于质量评估
- **NumPy (1.24+)**：数组操作和增量编码
- **SciPy (1.10+)**：科学计算工具
- **pyvips (2.2+)**：大文件快速图片处理

界面依赖：
- **Flask (3.0+)**：Web 服务器和 REST API
- **PySide6 (6.5+)**：基于 Qt 的 GUI
- **pyqtgraph (0.13+)**：统计可视化快速绘图

开发依赖（可选）：
- **pytest (7.0+)**：测试框架
- **pytest-cov (4.0+)**：覆盖率报告
- **ruff (0.1+)**：代码检查
- **mypy (1.0+)**：类型检查

## 安装过程

使用 pip 安装 KanTu：

```bash
# 基本安装
pip install kantu

# 包含开发工具
pip install kantu[dev]
```

或从源码安装：

```bash
# 克隆仓库
git clone https://github.com/cycleuser/KanTu.git
cd KanTu

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 开发模式安装
pip install -e ".[dev]"

# 运行测试验证安装
pytest tests/
```

## 使用方法

### 命令行界面

KanTu 为所有操作提供全面的 CLI：

```bash
# 在当前目录初始化图库
kantu init

# 添加图片到图库
kantu add image1.png image2.jpg

# 列出所有图片
kantu list

# 显示图库统计信息
kantu stats

# 查找与参考图片相似的图片
kantu similar reference.jpg

# 从图库导出图片
kantu export <image-id> -o output.png

# 删除图片
kantu remove <image-id>

# 配置设置
kantu config --similarity-threshold 0.9

# 启动 GUI
kantu gui

# 启动 Web 界面
kantu web --port 5000
```

### Python API

编程方式使用 KanTu：

```python
from kantu import init_gallery, add_image, list_images, export_image

# 初始化图库
init_gallery("/path/to/images")

# 添加图片
result = add_image("/path/to/new_image.jpg", "/path/to/gallery")
print(f"存储类型: {result.data['type']}")

# 列出图片
images = list_images("/path/to/gallery")
for img in images.data["images"]:
    print(f"{img['id']}: {img['width']}x{img['height']}")

# 导出图片
export_image("image_id", "output.png", "/path/to/gallery")
```

### Web 界面

启动 Web 服务器进行浏览器管理：

```bash
kantu web --host 0.0.0.0 --port 5000
```

访问 http://localhost:5000 获得响应式 Web 界面，支持：
- 图片预览和管理
- 拖放上传
- 统计仪表盘
- 批量操作

### GUI 应用程序

启动桌面应用程序：

```bash
kantu gui
```

功能包括：
- 带缩略图的图片网格视图
- 带元数据的预览面板
- 添加/删除/导出操作
- 统计显示

## 运行截图

| GUI 界面 | Web 界面 |
|:-------------:|:-------------:|
| ![GUI](images/gui.png) | ![Web](images/web.png) |

*占位符 - 将添加实际截图*

## 授权协议

KanTu 采用 GNU 通用公共许可证第 3 版或更高版本（GPLv3+）发布。详见 [LICENSE](LICENSE) 文件。

关键要点：
- 免费使用、修改和分发
- 修改必须在相同许可证下共享
- 按"原样"提供，不提供保证
- 完整条款见 LICENSE 文件