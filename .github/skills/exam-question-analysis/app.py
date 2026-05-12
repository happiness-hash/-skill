import os

from flask import Flask, render_template_string, request

from exam_analysis.web import HTML_TEMPLATE, build_web_context, run_web_analysis

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        try:
            result = run_web_analysis(request.form, os.path.dirname(__file__))
        except Exception as exc:
            result = str(exc)
    context = build_web_context(result=result)
    return render_template_string(HTML_TEMPLATE, **context)


if __name__ == '__main__':
    app.run(debug=True)
