from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import threading
import uuid
import time
from youtube_optimizer import YoutubeOptimizer
from youtube_fetcher import fetch_channel_videos

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/thumbnails'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global dictionary to store job status
JOBS = {}

def run_optimization_job(job_id, titles, output_dir, use_uuids=True):
    """
    Runs the optimization process in a background thread.
    Updates the JOBS dict with progress.
    """
    optimizer = YoutubeOptimizer()
    
    def progress_callback(current, total, title):
        JOBS[job_id]['current'] = current
        JOBS[job_id]['total'] = total
        JOBS[job_id]['current_title'] = title
        JOBS[job_id]['status'] = 'processing'

    try:
        results = optimizer.process_videos(
            titles, 
            output_dir=output_dir, 
            use_uuids=use_uuids, 
            progress_callback=progress_callback
        )
        JOBS[job_id]['results'] = results
        JOBS[job_id]['status'] = 'completed'
    except Exception as e:
        JOBS[job_id]['status'] = 'error'
        JOBS[job_id]['error'] = str(e)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/fetch_videos', methods=['POST'])
def fetch_videos():
    channel_url = request.form.get('channel_url')
    if not channel_url:
        return redirect(url_for('index'))
        
    videos = fetch_channel_videos(channel_url)
    return render_template('videos.html', videos=videos)

def create_job(titles, use_uuids=True):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'status': 'queued',
        'current': 0,
        'total': len(titles),
        'results': [],
        'error': None
    }
    
    thread = threading.Thread(
        target=run_optimization_job,
        args=(job_id, titles, app.config['UPLOAD_FOLDER'], use_uuids)
    )
    thread.start()
    return job_id

@app.route('/generate_selection', methods=['POST'])
def generate_selection():
    selected_titles = request.form.getlist('selected_titles')
    
    if not selected_titles:
        return redirect(url_for('index'))

    job_id = create_job(selected_titles, use_uuids=False)
    return render_template('progress.html', job_id=job_id)

@app.route('/generate', methods=['POST'])
def generate():
    titles_input = request.form.get('titles')
    if not titles_input:
        return redirect(url_for('index'))

    # Split by newlines and filter empty lines
    titles = [t.strip() for t in titles_input.split('\n') if t.strip()]
    
    # Limit to 10 for safety/cost
    titles = titles[:10]

    job_id = create_job(titles, use_uuids=True)
    return render_template('progress.html', job_id=job_id)

@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'unknown'}), 404
    return jsonify(job)

@app.route('/results/<job_id>', methods=['GET'])
def job_results(job_id):
    job = JOBS.get(job_id)
    if not job or job['status'] != 'completed':
        return redirect(url_for('index'))
    return render_template('results.html', results=job['results'])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
