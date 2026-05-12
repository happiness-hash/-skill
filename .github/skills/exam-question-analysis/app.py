import os

from flask import Flask, jsonify, render_template_string, request

from exam_analysis.web import HTML_TEMPLATE, build_web_context, get_task, start_web_analysis

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    context = build_web_context()
    return render_template_string(HTML_TEMPLATE, **context)


@app.route('/start', methods=['POST'])
def start():
    try:
        task_id = start_web_analysis(request.form)
    except Exception as exc:
        return jsonify({'detail': '启动失败', 'result': str(exc)}), 400
    return jsonify({'task_id': task_id})


@app.route('/status/<task_id>', methods=['GET'])
def status(task_id):
    return jsonify(get_task(task_id))


if __name__ == '__main__':
    app.run(debug=True)
