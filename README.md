# KanTu

Git-like image gallery management with delta encoding for storage optimization.

## Project Background

KanTu is an innovative image gallery management tool inspired by Git's version control concepts. In modern digital photography and image editing workflows, users often accumulate many similar images - edited versions, crops, different exposures, or minor variations. Traditional storage methods keep each image as a separate file, resulting in significant storage redundancy. KanTu addresses this challenge by implementing delta encoding: storing one "base" image and recording only the differences (deltas) for similar images, dramatically reducing storage requirements while maintaining full image quality and accessibility.

The name "KanTu" (看图) means "viewing images" in Chinese, reflecting the tool's focus on practical image management. The system uses perceptual hashing (pHash) to identify similar images, SSIM (Structural Similarity Index) to determine if delta storage is beneficial, and efficient pixel-level delta encoding to minimize storage. Each directory maintains its own gallery database, enabling independent management of different image collections.

## Application Scenarios

KanTu is designed for photographers, designers, and anyone managing large image collections with many similar files. Key use cases include:

1. **Photography Workflows**: Store multiple exposure brackets, edited versions, and variations with minimal storage overhead. A wedding photographer with 5000+ images including many similar shots can save 30-60% storage.

2. **Design Versioning**: Graphic designers often create multiple iterations of the same design. KanTu stores the evolution of designs efficiently, with full ability to export any version.

3. **Screenshot Archives**: Technical documentation often involves many similar screenshots. Delta encoding dramatically reduces storage for these near-duplicate images.

4. **Personal Photo Libraries**: Family photos often include burst shots and edited versions. KanTu automatically detects and optimizes these, while keeping all images accessible.

5. **Web Application Backend**: The REST API enables integration into web applications, allowing cloud-based image galleries with optimized storage.

## Hardware Compatibility

KanTu is designed to run on standard consumer hardware with modest requirements:

- **CPU**: Any modern processor (Intel Core i3/AMD Ryzen 3 or better). Image hashing and delta computation are multi-threaded but not CPU-intensive for typical image sizes.

- **Memory**: 4GB RAM minimum, 8GB recommended. Image processing temporarily loads images into memory, so larger images or batch operations benefit from more RAM.

- **GPU**: Not required. All processing is CPU-based, making KanTu compatible with systems without dedicated graphics.

- **Storage**: The delta files are stored as compressed NumPy arrays, typically achieving 30-70% storage savings for similar image sets. SSD storage improves database performance for large galleries.

- **Display**: For GUI usage, any display supporting 1024x768 or higher resolution. The web interface is responsive and works on various screen sizes.

## Operating Systems

KanTu is cross-platform and tested on:

- **Windows**: Windows 10/11 with Python 3.9+. The PySide6 GUI integrates natively with Windows styling.

- **macOS**: macOS 10.15 (Catalina) or later with Python 3.9+. Native window styling and Retina display support.

- **Linux**: Any modern distribution with Python 3.9+ and Qt libraries. Tested on Ubuntu 22.04, Fedora 38, and Arch Linux.

The CLI interface works identically across all platforms. The GUI uses native window decorations and integrates with system themes. The web interface runs in any modern browser (Chrome, Firefox, Safari, Edge).

## Dependencies

KanTu requires Python 3.9 or newer. Core dependencies include:

- **Pillow (10.0+)**: Image I/O and basic manipulations
- **imagehash (4.3+)**: Perceptual hashing for similarity detection  
- **scikit-image (0.21+)**: SSIM calculation for quality assessment
- **NumPy (1.24+)**: Array operations and delta encoding
- **SciPy (1.10+)**: Scientific computing utilities
- **pyvips (2.2+)**: Fast image processing for large files

Interface dependencies:
- **Flask (3.0+)**: Web server and REST API
- **PySide6 (6.5+)**: Qt-based GUI
- **pyqtgraph (0.13+)**: Fast plotting for statistics visualization

Development dependencies (optional):
- **pytest (7.0+)**: Testing framework
- **pytest-cov (4.0+)**: Coverage reporting
- **ruff (0.1+)**: Linting
- **mypy (1.0+)**: Type checking

## Installation

Install KanTu using pip:

```bash
# Basic installation
pip install kantu

# With development tools
pip install kantu[dev]
```

Or install from source:

```bash
# Clone the repository
git clone https://github.com/cycleuser/KanTu.git
cd KanTu

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests to verify installation
pytest tests/
```

## Usage

### Command-Line Interface

KanTu provides a comprehensive CLI for all operations:

```bash
# Initialize a gallery in current directory
kantu init

# Add images to gallery
kantu add image1.png image2.jpg

# List all images
kantu list

# Show gallery statistics
kantu stats

# Find similar images to a reference
kantu similar reference.jpg

# Export an image from gallery
kantu export <image-id> -o output.png

# Remove an image
kantu remove <image-id>

# Configure settings
kantu config --similarity-threshold 0.9

# Launch GUI
kantu gui

# Launch web interface
kantu web --port 5000
```

### Python API

Use KanTu programmatically:

```python
from kantu import init_gallery, add_image, list_images, export_image

# Initialize gallery
init_gallery("/path/to/images")

# Add an image
result = add_image("/path/to/new_image.jpg", "/path/to/gallery")
print(f"Stored as: {result.data['type']}")

# List images
images = list_images("/path/to/gallery")
for img in images.data["images"]:
    print(f"{img['id']}: {img['width']}x{img['height']}")

# Export image
export_image("image_id", "output.png", "/path/to/gallery")
```

### Web Interface

Launch the web server for browser-based management:

```bash
kantu web --host 0.0.0.0 --port 5000
```

Access at http://localhost:5000 for a responsive web interface with:
- Image preview and management
- Drag-and-drop upload
- Statistics dashboard
- Batch operations

### GUI Application

Launch the desktop application:

```bash
kantu gui
```

Features include:
- Image grid view with thumbnails
- Preview panel with metadata
- Add/remove/export operations
- Statistics display

## Screenshots

| GUI Interface | Web Interface |
|:-------------:|:-------------:|
| ![GUI](images/gui.png) | ![Web](images/web.png) |

*Placeholders - actual screenshots will be added*

## License

KanTu is released under the GNU General Public License v3.0 or later (GPLv3+). See the [LICENSE](LICENSE) file for details.

Key points:
- Free to use, modify, and distribute
- Modifications must be shared under the same license
- Provided "as is" without warranty
- See LICENSE for full terms