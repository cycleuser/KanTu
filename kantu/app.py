"""Flask web application for KanTu."""

import io
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

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
    return render_template("index.html")


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
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True)
        (templates_dir / "index.html").write_text(INDEX_HTML)
    print(f"Starting KanTu web server at http://{host}:{port}")
    print(f"Gallery path: {Path(gallery_path).resolve()}")
    app.run(host=host, port=port, debug=False)


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KanTu - Image Gallery Manager</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 1.5rem; }
        .stats { display: flex; gap: 2rem; }
        .stat { text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: bold; }
        .stat-label { font-size: 0.8rem; opacity: 0.8; }
        .container { max-width: 1400px; margin: 2rem auto; padding: 0 1rem; }
        .toolbar { background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; gap: 1rem; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn { padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn:hover { opacity: 0.9; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
        .image-card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; }
        .image-card:hover { transform: translateY(-4px); }
        .image-card img { width: 100%; height: 150px; object-fit: cover; }
        .image-card .info { padding: 0.5rem; }
        .image-card .id { font-family: monospace; font-size: 0.8rem; color: #666; }
        .image-card .type { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; margin-top: 0.25rem; }
        .type-base { background: #27ae60; color: white; }
        .type-delta { background: #f39c12; color: white; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: white; padding: 2rem; border-radius: 8px; max-width: 800px; max-height: 90vh; overflow: auto; }
        .modal img { max-width: 100%; max-height: 400px; }
        .modal-actions { margin-top: 1rem; display: flex; gap: 1rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>KanTu</h1>
        <div class="stats">
            <div class="stat"><div class="stat-value" id="total-images">0</div><div class="stat-label">Images</div></div>
            <div class="stat"><div class="stat-value" id="base-images">0</div><div class="stat-label">Base</div></div>
            <div class="stat"><div class="stat-value" id="delta-images">0</div><div class="stat-label">Delta</div></div>
            <div class="stat"><div class="stat-value" id="savings">0%</div><div class="stat-label">Saved</div></div>
        </div>
    </div>
    <div class="container">
        <div class="toolbar">
            <button class="btn btn-primary" onclick="initGallery()">Init Gallery</button>
            <input type="file" id="file-input" multiple accept="image/*" style="display:none" onchange="uploadFiles(this.files)">
            <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">Add Images</button>
            <button class="btn btn-primary" onclick="refreshGallery()">Refresh</button>
        </div>
        <div class="gallery" id="gallery"></div>
    </div>
    <div class="modal" id="modal">
        <div class="modal-content">
            <img id="modal-image" src="" alt="Preview">
            <div id="modal-info" style="margin-top:1rem"></div>
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="exportImage()">Export</button>
                <button class="btn btn-danger" onclick="deleteImage()">Delete</button>
                <button class="btn" onclick="closeModal()">Close</button>
            </div>
        </div>
    </div>
    <script>
        let currentImageId = null;
        async function fetchAPI(endpoint, options = {}) {
            const response = await fetch('/api' + endpoint, options);
            return response.json();
        }
        async function refreshGallery() {
            const [imagesRes, statsRes] = await Promise.all([
                fetchAPI('/images?limit=1000'),
                fetchAPI('/stats')
            ]);
            if (imagesRes.success) renderGallery(imagesRes.data.images);
            if (statsRes.success) updateStats(statsRes.data);
        }
        function renderGallery(images) {
            const gallery = document.getElementById('gallery');
            gallery.innerHTML = images.map(img => `
                <div class="image-card" onclick="showImage('${img.id}')">
                    <img src="/api/images/${img.id}/preview" alt="${img.id}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 150%22><rect fill=%22%23ddd%22 width=%22200%22 height=%22150%22/><text x=%22100%22 y=%2275%22 text-anchor=%22middle%22 fill=%22%23999%22>No Preview</text></svg>'">
                    <div class="info">
                        <div class="id">${img.id.substring(0,12)}...</div>
                        <span class="type ${img.is_base ? 'type-base' : 'type-delta'}">${img.is_base ? 'Base' : 'Delta'}</span>
                    </div>
                </div>
            `).join('');
        }
        function updateStats(stats) {
            document.getElementById('total-images').textContent = stats.total_images;
            document.getElementById('base-images').textContent = stats.base_images;
            document.getElementById('delta-images').textContent = stats.delta_images;
            document.getElementById('savings').textContent = (stats.savings_ratio * 100).toFixed(1) + '%';
        }
        async function initGallery() {
            const result = await fetchAPI('/init', { method: 'POST' });
            alert(result.success ? 'Gallery initialized!' : 'Error: ' + result.error);
            refreshGallery();
        }
        async function uploadFiles(files) {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                await fetchAPI('/images', { method: 'POST', body: formData });
            }
            refreshGallery();
        }
        function showImage(id) {
            currentImageId = id;
            document.getElementById('modal-image').src = `/api/images/${id}/preview`;
            document.getElementById('modal').classList.add('active');
        }
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
            currentImageId = null;
        }
        async function exportImage() {
            if (currentImageId) {
                window.location.href = `/api/images/${currentImageId}/export`;
            }
        }
        async function deleteImage() {
            if (currentImageId && confirm('Delete this image?')) {
                const result = await fetchAPI(`/images/${currentImageId}`, { method: 'DELETE' });
                alert(result.success ? 'Image deleted!' : 'Error: ' + result.error);
                closeModal();
                refreshGallery();
            }
        }
        refreshGallery();
    </script>
</body>
</html>"""


if __name__ == "__main__":
    run_server()
