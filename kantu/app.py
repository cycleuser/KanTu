"""Flask web application for KanTu with elegant modern design."""

import io
import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file

from kantu.api import (
    ToolResult,
    add_image,
    export_image,
    find_similar,
    get_gallery_stats,
    get_image_info,
    init_gallery,
    list_images,
    remove_image,
    set_config,
)
from kantu.core import KanTuCore

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
GALLERY_PATH = "."


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/init", methods=["POST"])
def api_init():
    result = init_gallery(GALLERY_PATH)
    return jsonify(result.to_dict())


@app.route("/api/images", methods=["GET"])
def api_list_images():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    result = list_images(GALLERY_PATH, limit, offset)
    return jsonify(result.to_dict())


@app.route("/api/images", methods=["POST"])
def api_add_image():
    if "file" not in request.files:
        return jsonify(ToolResult(False, error="No file provided").to_dict()), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify(ToolResult(False, error="No file selected").to_dict()), 400
    temp_dir = Path(GALLERY_PATH) / ".kantu" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename
    file.save(temp_path)
    threshold = request.form.get("threshold", type=float)
    force_base = request.form.get("force_base", "false").lower() == "true"
    result = add_image(
        str(temp_path), GALLERY_PATH, similarity_threshold=threshold, force_base=force_base
    )
    try:
        os.remove(temp_path)
    except Exception:
        pass
    return jsonify(result.to_dict())


@app.route("/api/images/<image_id>", methods=["GET"])
def api_get_image(image_id):
    result = get_image_info(image_id, GALLERY_PATH)
    return jsonify(result.to_dict())


@app.route("/api/images/<image_id>", methods=["DELETE"])
def api_delete_image(image_id):
    result = remove_image(image_id, GALLERY_PATH)
    return jsonify(result.to_dict())


@app.route("/api/images/<image_id>/export", methods=["GET"])
def api_export_image(image_id):
    output_dir = Path(GALLERY_PATH) / ".kantu" / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{image_id}.png"
    result = export_image(image_id, str(output_path), GALLERY_PATH)
    if result.success:
        return send_file(output_path, as_attachment=True, download_name=f"{image_id}.png")
    return jsonify(result.to_dict()), 400


@app.route("/api/images/<image_id>/preview", methods=["GET"])
def api_preview_image(image_id):
    core = KanTuCore(GALLERY_PATH)
    if not core.is_initialized():
        return jsonify(ToolResult(False, error="Gallery not initialized").to_dict()), 400
    arr = core.reconstruct_image(image_id)
    if arr is None:
        return jsonify(ToolResult(False, error="Image not found").to_dict()), 404
    from PIL import Image

    img = Image.fromarray(arr)
    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


@app.route("/api/similar", methods=["POST"])
def api_find_similar():
    if "file" not in request.files:
        return jsonify(ToolResult(False, error="No file provided").to_dict()), 400
    file = request.files["file"]
    temp_dir = Path(GALLERY_PATH) / ".kantu" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename
    file.save(temp_path)
    threshold = request.form.get("threshold", 10, type=int)
    result = find_similar(str(temp_path), GALLERY_PATH, threshold)
    try:
        os.remove(temp_path)
    except Exception:
        pass
    return jsonify(result.to_dict())


@app.route("/api/stats", methods=["GET"])
def api_stats():
    result = get_gallery_stats(GALLERY_PATH)
    return jsonify(result.to_dict())


@app.route("/api/config", methods=["GET", "PUT"])
def api_config():
    if request.method == "GET":
        core = KanTuCore(GALLERY_PATH)
        if not core.is_initialized():
            return jsonify(ToolResult(False, error="Gallery not initialized").to_dict()), 400
        core._load_config()
        return jsonify(
            ToolResult(
                True,
                data={
                    "similarity_threshold": core.config.similarity_threshold,
                    "min_delta_ratio": core.config.min_delta_ratio,
                    "max_hamming_distance": core.config.max_hamming_distance,
                },
            ).to_dict()
        )
    else:
        data = request.json or {}
        result = set_config(
            GALLERY_PATH,
            similarity_threshold=data.get("similarity_threshold"),
            min_delta_ratio=data.get("min_delta_ratio"),
            max_hamming_distance=data.get("max_hamming_distance"),
        )
        return jsonify(result.to_dict())


def run_server(host: str = "127.0.0.1", port: int = 5000, gallery_path: str = "."):
    global GALLERY_PATH
    GALLERY_PATH = gallery_path
    print(f"Starting KanTu web server at http://{host}:{port}")
    print(f"Gallery path: {Path(gallery_path).resolve()}")
    app.run(host=host, port=port, debug=False)


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KanTu - Image Gallery Manager</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --bg-hover: #22222e;
            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
            --accent-success: #00d9a0;
            --accent-warning: #fbbf24;
            --accent-danger: #f43f5e;
            --accent-info: #38bdf8;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --text-muted: #606070;
            --border-color: #2a2a36;
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-success: linear-gradient(135deg, #00d9a0 0%, #00b386 100%);
            --gradient-danger: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 20px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 8px 40px rgba(0, 0, 0, 0.5);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 20px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        .app-container { min-height: 100vh; }
        
        /* Header */
        .header {
            background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 24px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(20px);
        }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-icon {
            width: 48px;
            height: 48px;
            background: var(--gradient-primary);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: var(--shadow-md);
        }
        .brand-text h1 {
            font-size: 24px;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .brand-text p {
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Stats */
        .stats-container {
            display: flex;
            gap: 24px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 16px 24px;
            min-width: 120px;
            text-align: center;
            transition: var(--transition);
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        .stat-value {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .stat-card:nth-child(1) .stat-value { color: var(--accent-primary); }
        .stat-card:nth-child(2) .stat-value { color: var(--accent-info); }
        .stat-card:nth-child(3) .stat-value { color: #f472b6; }
        .stat-card:nth-child(4) .stat-value { color: var(--accent-success); }
        .stat-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        
        /* Main Content */
        .main-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
        }
        
        /* Toolbar */
        .toolbar {
            display: flex;
            gap: 16px;
            margin-bottom: 32px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: var(--gradient-primary);
            color: white;
            box-shadow: var(--shadow-sm);
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        .btn-secondary {
            background: var(--bg-card);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }
        .btn-secondary:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        .btn-danger {
            background: var(--gradient-danger);
            color: white;
        }
        .btn-danger:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        /* Gallery Grid */
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
        }
        .image-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            overflow: hidden;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
        }
        .image-card:hover {
            transform: translateY(-8px);
            box-shadow: var(--shadow-lg);
            border-color: var(--accent-primary);
        }
        .image-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient-primary);
            opacity: 0;
            transition: var(--transition);
        }
        .image-card:hover::before {
            opacity: 1;
        }
        .image-preview {
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: var(--bg-secondary);
        }
        .image-info {
            padding: 16px;
        }
        .image-id {
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .image-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .type-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .type-badge.base {
            background: rgba(0, 217, 160, 0.15);
            color: var(--accent-success);
        }
        .type-badge.delta {
            background: rgba(244, 114, 182, 0.15);
            color: #f472b6;
        }
        .image-size {
            font-size: 12px;
            color: var(--text-muted);
        }
        
        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(10px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: 32px;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
            animation: modalIn 0.3s ease-out;
        }
        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95) translateY(20px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .modal-header {
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-title {
            font-size: 18px;
            font-weight: 600;
        }
        .modal-close {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 24px;
            cursor: pointer;
            padding: 8px;
            border-radius: var(--radius-sm);
            transition: var(--transition);
        }
        .modal-close:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        .modal-body {
            padding: 24px;
            display: flex;
            gap: 24px;
        }
        .modal-image {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-secondary);
            border-radius: var(--radius-md);
            overflow: hidden;
            min-height: 300px;
        }
        .modal-image img {
            max-width: 100%;
            max-height: 400px;
            object-fit: contain;
        }
        .modal-details {
            width: 250px;
        }
        .detail-item {
            margin-bottom: 20px;
        }
        .detail-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .detail-value {
            font-size: 16px;
            font-weight: 500;
        }
        .modal-actions {
            padding: 16px 24px;
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 80px 32px;
            color: var(--text-muted);
        }
        .empty-icon {
            font-size: 64px;
            margin-bottom: 24px;
            opacity: 0.5;
        }
        .empty-title {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .empty-desc {
            font-size: 14px;
            margin-bottom: 24px;
        }
        
        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border-color);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Toast */
        .toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 2000;
        }
        .toast {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 16px 24px;
            margin-top: 8px;
            box-shadow: var(--shadow-lg);
            animation: toastIn 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .toast.success { border-left: 4px solid var(--accent-success); }
        .toast.error { border-left: 4px solid var(--accent-danger); }
        @keyframes toastIn {
            from { opacity: 0; transform: translateX(100%); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        /* File Input */
        .file-input-wrapper {
            position: relative;
        }
        .file-input {
            position: absolute;
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header-content { flex-direction: column; gap: 20px; }
            .stats-container { flex-wrap: wrap; justify-content: center; }
            .stat-card { min-width: 100px; padding: 12px 16px; }
            .modal-body { flex-direction: column; }
            .modal-details { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header class="header">
            <div class="header-content">
                <div class="brand">
                    <div class="brand-icon">◈</div>
                    <div class="brand-text">
                        <h1>KanTu</h1>
                        <p>Image Gallery Manager</p>
                    </div>
                </div>
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-value" id="stat-total">0</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-base">0</div>
                        <div class="stat-label">Base</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-delta">0</div>
                        <div class="stat-label">Delta</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="stat-saved">0%</div>
                        <div class="stat-label">Saved</div>
                    </div>
                </div>
            </div>
        </header>
        
        <main class="main-content">
            <div class="toolbar">
                <button class="btn btn-primary" onclick="initGallery()">
                    <span>✦</span> Initialize Gallery
                </button>
                <div class="file-input-wrapper">
                    <input type="file" id="file-input" class="file-input" multiple accept="image/*" onchange="uploadFiles(this.files)">
                    <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">
                        <span>+</span> Add Images
                    </button>
                </div>
                <button class="btn btn-secondary" onclick="refreshGallery()">
                    <span>↻</span> Refresh
                </button>
            </div>
            
            <div class="gallery-grid" id="gallery"></div>
        </main>
    </div>
    
    <div class="modal-overlay" id="modal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2 class="modal-title">Image Preview</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-image">
                    <img id="modal-img" src="" alt="Preview">
                </div>
                <div class="modal-details">
                    <div class="detail-item">
                        <div class="detail-label">Image ID</div>
                        <div class="detail-value" id="modal-id">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Type</div>
                        <div class="detail-value" id="modal-type">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Dimensions</div>
                        <div class="detail-value" id="modal-dim">-</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Similarity</div>
                        <div class="detail-value" id="modal-sim">-</div>
                    </div>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                <button class="btn btn-primary" onclick="exportImage()">↓ Export</button>
                <button class="btn btn-danger" onclick="deleteImage()">✕ Delete</button>
            </div>
        </div>
    </div>
    
    <div class="toast-container" id="toast-container"></div>
    
    <script>
        let currentImageId = null;
        let currentImageData = null;
        
        async function fetchAPI(endpoint, options = {}) {
            try {
                const response = await fetch('/api' + endpoint, options);
                return await response.json();
            } catch (e) {
                return { success: false, error: 'Network error' };
            }
        }
        
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }
        
        async function refreshGallery() {
            const [imagesRes, statsRes] = await Promise.all([
                fetchAPI('/images?limit=1000'),
                fetchAPI('/stats')
            ]);
            
            if (imagesRes.success) renderGallery(imagesRes.data.images);
            if (statsRes.success) updateStats(statsRes.data);
        }
        
        function updateStats(stats) {
            document.getElementById('stat-total').textContent = stats.total_images;
            document.getElementById('stat-base').textContent = stats.base_images;
            document.getElementById('stat-delta').textContent = stats.delta_images;
            document.getElementById('stat-saved').textContent = (stats.savings_ratio * 100).toFixed(1) + '%';
        }
        
        function renderGallery(images) {
            const gallery = document.getElementById('gallery');
            
            if (!images.length) {
                gallery.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <div class="empty-icon">◈</div>
                        <div class="empty-title">No images yet</div>
                        <div class="empty-desc">Initialize the gallery and add some images to get started</div>
                    </div>
                `;
                return;
            }
            
            gallery.innerHTML = images.map(img => `
                <div class="image-card" onclick="showImage('${img.id}')">
                    <img class="image-preview" 
                         src="/api/images/${img.id}/preview" 
                         alt="${img.id}"
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 280 200%22><rect fill=%22%2312121a%22 width=%22280%22 height=%22200%22/><text x=%22140%22 y=%22100%22 text-anchor=%22middle%22 fill=%22%23404050%22 font-size=%2240%22>◈</text></svg>'">
                    <div class="image-info">
                        <div class="image-id">${img.id.substring(0, 16)}...</div>
                        <div class="image-meta">
                            <span class="type-badge ${img.is_base ? 'base' : 'delta'}">${img.is_base ? 'Base' : 'Delta'}</span>
                            <span class="image-size">${img.width}×${img.height}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        async function initGallery() {
            const result = await fetchAPI('/init', { method: 'POST' });
            if (result.success) {
                showToast('Gallery initialized successfully');
                refreshGallery();
            } else {
                showToast(result.error || 'Failed to initialize', 'error');
            }
        }
        
        async function uploadFiles(files) {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                const result = await fetchAPI('/images', { method: 'POST', body: formData });
                if (!result.success) {
                    showToast(`Failed to add ${file.name}: ${result.error}`, 'error');
                }
            }
            showToast('Images added successfully');
            refreshGallery();
        }
        
        async function showImage(id) {
            currentImageId = id;
            const result = await fetchAPI(`/images/${id}`);
            
            if (result.success) {
                currentImageData = result.data;
                document.getElementById('modal-img').src = `/api/images/${id}/preview`;
                document.getElementById('modal-id').textContent = id.substring(0, 16) + '...';
                document.getElementById('modal-type').textContent = result.data.is_base ? 'Base Image' : 'Delta Image';
                document.getElementById('modal-dim').textContent = `${result.data.width} × ${result.data.height}`;
                document.getElementById('modal-sim').textContent = result.data.is_base ? 'N/A' : (result.data.similarity_score * 100).toFixed(1) + '%';
                document.getElementById('modal').classList.add('active');
            }
        }
        
        function closeModal(e) {
            if (!e || e.target.classList.contains('modal-overlay')) {
                document.getElementById('modal').classList.remove('active');
                currentImageId = null;
            }
        }
        
        function exportImage() {
            if (currentImageId) {
                window.location.href = `/api/images/${currentImageId}/export`;
                showToast('Image exported');
            }
        }
        
        async function deleteImage() {
            if (currentImageId && confirm('Delete this image?')) {
                const result = await fetchAPI(`/images/${currentImageId}`, { method: 'DELETE' });
                if (result.success) {
                    showToast('Image deleted');
                    closeModal();
                    refreshGallery();
                } else {
                    showToast(result.error || 'Failed to delete', 'error');
                }
            }
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
        
        // Initial load
        refreshGallery();
    </script>
</body>
</html>"""
