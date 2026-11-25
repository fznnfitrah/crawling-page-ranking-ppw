import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from crawler import crawl_website
from pagerank import calculate_pagerank_analysis

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/api/crawl", methods=["POST"])
def run_crawl():
    data = request.get_json(silent=True) or {}
    start_url = (data.get("url") or "").strip()
    raw_depth = data.get("depth", 2)

    if not start_url:
        return jsonify({"error": "Field 'url' wajib diisi."}), 400

    try:
        depth = int(raw_depth)
        if depth < 0:
            return jsonify({"error": "Kedalaman (depth) tidak boleh negatif."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Kedalaman (depth) harus berupa angka bulat."}), 400

    # Nilai batas aman agar tetap menampung banyak node tanpa membuat server hang
    max_pages = int(data.get("max_pages", 250))
    max_links_per_page = int(data.get("max_links_per_page", 40))

    try:
        crawl_data = crawl_website(
            start_url=start_url,
            max_depth=depth,
            max_pages=max_pages,
            max_links_per_page=max_links_per_page,
            timeout=5.0,
        )
        analysis = calculate_pagerank_analysis(crawl_data, top_n=10)

        return jsonify({
            "seed_url": crawl_data["seed_url"],
            "max_depth": crawl_data["max_depth"],
            "stats": {
                "crawled_pages": crawl_data["crawled_pages_count"],
                "total_nodes": crawl_data["total_nodes"],
                "total_edges": crawl_data["total_edges"],
                "error_count": len(crawl_data["errors"]),
            },
            "graph": {
                "nodes": analysis["graph_nodes"],
                "edges": analysis["graph_edges"],
            },
            "top_10": analysis["top_10"],
            "errors": crawl_data["errors"],
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Terjadi kesalahan saat memproses crawling: {exc}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
