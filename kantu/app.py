"""Flask web application for KanTu."""

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
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #fff; color: #333; }
        h1 { margin: 0 0 20px 0; font-size: 24px; }
        .stats { display: flex; gap: 24px; margin-bottom: 20px; padding: 16px; background: #f5f5f5; border-radius: 8px; }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; }
        .stat-label { font-size: 12px; color: #666; }
        .toolbar { margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap; }
        button { padding: 8px 16px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 14px; }
        button:hover { background: #f0f0f0; }
        button.primary { background: #0066cc; color: #fff; border-color: #0066cc; }
        button.primary:hover { background: #0055aa; }
        button.danger { background: #cc3333; color: #fff; border-color: #cc3333; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
        .card { border: 1px solid #ddd; border-radius: 8px; overflow: hidden; cursor: pointer; }
        .card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card img { width: 100%; height: 150px; object-fit: cover; background: #f5f5f5; }
        .card-body { padding: 12px; }
        .card-id { font-family: monospace; font-size: 12px; color: #666; margin-bottom: 4px; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
        .badge.base { background: #e6f3e6; color: #006600; }
        .badge.delta { background: #fff3e6; color: #cc6600; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: #fff; padding: 24px; border-radius: 8px; max-width: 700px; width: 90%; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .modal-header h2 { margin: 0; font-size: 18px; }
        .modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: #999; }
        .modal-body { display: flex; gap: 16px; }
        .modal-image { flex: 1; text-align: center; }
        .modal-image img { max-width: 100%; max-height: 300px; }
        .modal-info { width: 200px; }
        .modal-info p { margin: 0 0 8px 0; }
        .modal-info label { font-size: 11px; color: #666; text-transform: uppercase; }
        .modal-actions { margin-top: 16px; display: flex; gap: 8px; }
        input[type="file"] { display: none; }
        .empty { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <h1>KanTu</h1>
    <div class="stats">
        <div class="stat"><div class="stat-value" id="stat-total">0</div><div class="stat-label">Total</div></div>
        <div class="stat"><div class="stat-value" id="stat-base">0</div><div class="stat-label">Base</div></div>
        <div class="stat"><div class="stat-value" id="stat-delta">0</div><div class="stat-label">Delta</div></div>
        <div class="stat"><div class="stat-value" id="stat-saved">0%</div><div class="stat-label">Saved</div></div>
    </div>
    <div class="toolbar">
        <button class="primary" onclick="initGallery()">Init Gallery</button>
        <input type="file" id="file-input" multiple accept="image/*" onchange="uploadFiles(this.files)">
        <button class="primary" onclick="document.getElementById('file-input').click()">Add Images</button>
        <button onclick="refreshGallery()">Refresh</button>
    </div>
    <div class="gallery" id="gallery"></div>
    <div class="modal" id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Image Preview</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-image"><img id="modal-img" src="" alt="Preview"></div>
                <div class="modal-info">
                    <p><label>ID</label><br><span id="modal-id">-</span></p>
                    <p><label>Type</label><br><span id="modal-type">-</span></p>
                    <p><label>Dimensions</label><br><span id="modal-dim">-</span></p>
                    <p><label>Similarity</label><br><span id="modal-sim">-</span></p>
                </div>
            </div>
            <div class="modal-actions">
                <button onclick="closeModal()">Close</button>
                <button class="primary" onclick="exportImage()">Export</button>
                <button class="danger" onclick="deleteImage()">Delete</button>
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
            const [imagesRes, statsRes] = await Promise.all([fetchAPI('/images?limit=1000'), fetchAPI('/stats')]);
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
                gallery.innerHTML = '<div class="empty">No images. Initialize gallery and add images to get started.</div>';
                return;
            }
            gallery.innerHTML = images.map(img => `
                <div class="card" onclick="showImage('${img.id}')">
                    <img src="/api/images/${img.id}/preview" alt="${img.id}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 150%22><rect fill=%22%23f5f5f5%22 width=%22200%22 height=%22150%22/><text x=%22100%22 y=%2275%22 text-anchor=%22middle%22 fill=%22%23999%22>No Preview</text></svg>'">
                    <div class="card-body">
                        <div class="card-id">${img.id.substring(0, 12)}...</div>
                        <span class="badge ${img.is_base ? 'base' : 'delta'}">${img.is_base ? 'Base' : 'Delta'}</span>
                    </div>
                </div>
            `).join('');
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
        async function showImage(id) {
            currentImageId = id;
            const result = await fetchAPI(`/images/${id}`);
            if (result.success) {
                document.getElementById('modal-img').src = `/api/images/${id}/preview`;
                document.getElementById('modal-id').textContent = id.substring(0, 16) + '...';
                document.getElementById('modal-type').textContent = result.data.is_base ? 'Base' : 'Delta';
                document.getElementById('modal-dim').textContent = `${result.data.width} × ${result.data.height}`;
                document.getElementById('modal-sim').textContent = result.data.is_base ? 'N/A' : (result.data.similarity_score * 100).toFixed(1) + '%';
                document.getElementById('modal').classList.add('active');
            }
        }
        function closeModal() { document.getElementById('modal').classList.remove('active'); currentImageId = null; }
        function exportImage() { if (currentImageId) window.location.href = `/api/images/${currentImageId}/export`; }
        async function deleteImage() {
            if (currentImageId && confirm('Delete this image?')) {
                const result = await fetchAPI(`/images/${currentImageId}`, { method: 'DELETE' });
                alert(result.success ? 'Deleted!' : 'Error: ' + result.error);
                closeModal();
                refreshGallery();
            }
        }
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        refreshGallery();
    </script>
</body>
</html>"""


if __name__ == "__main__":
    run_server()
