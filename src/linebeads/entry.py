from argparse import ArgumentParser
from functools import lru_cache
import json
from pathlib import Path
import re

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from .pipeline import DISPLAY, MODULES, execute, open_fixture, preview

app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
app.config['MAX_CONTENT_LENGTH'] = 1_500_000
app.json.sort_keys = False


def validate_parameters(capacity, strategy):
    if type(capacity) is not int or not 1 <= capacity <= 60:
        raise ValueError('额度应是 1 到 60 的整数')
    if not isinstance(strategy, str) or strategy not in {'balanced', 'focus'}:
        raise ValueError('策略应是 balanced 或 focus')
    return capacity, strategy


@lru_cache(maxsize=8)
def sample(capacity=12, strategy='balanced'):
    return preview(capacity, strategy)


@app.get('/')
def home():
    return render_template('desk.html', modules=MODULES, display=DISPLAY)


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'linebeads'}


@app.get('/api/linebeads/overview')
def overview():
    return jsonify(sample())


@app.post('/api/linebeads/run')
def run_case():
    try:
        posted = request.get_json()
        if not isinstance(posted, dict) or posted.keys() - {'capacity', 'strategy', 'records', 'as_of'}:
            raise ValueError('请求字段无效')
        mode = posted.get('strategy', 'balanced')
        capacity, strategy = validate_parameters(posted.get('capacity', 12), mode)
        if 'records' not in posted:
            if 'as_of' in posted:
                raise ValueError('导入截止日需要同时提交 records')
            return jsonify(sample(capacity, strategy))
        as_of = posted.get('as_of', 96)
        if type(as_of) is not int or not 91 <= as_of <= 3650:
            raise ValueError('截止日须在第 91 日后')
        return jsonify(execute(posted['records'], capacity, strategy, as_of=as_of))
    except (BadRequest, UnsupportedMediaType):
        return jsonify(code='INVALID_JSON', message='请提交 JSON 对象'), 400
    except ValueError as issue:
        return jsonify(code='INVALID_BATCH', message=str(issue)), 422


@app.get('/api/linebeads/stages/<stage>')
def stage_detail(stage):
    mapping = {slug: index for index, (slug, _) in enumerate(MODULES)}
    if stage not in mapping:
        return jsonify(code='UNKNOWN_STAGE', message='未找到业务环节'), 404
    try:
        raw = request.args.get('capacity', '12')
        if not re.fullmatch(r'[0-9]{1,2}', raw):
            raise ValueError('额度应是 1 到 60 的整数')
        capacity, strategy = validate_parameters(int(raw), request.args.get('strategy', 'balanced'))
    except ValueError as issue:
        return jsonify(code='INVALID_BATCH', message=str(issue)), 422
    result = sample(capacity, strategy)
    return jsonify(run_id=result['run_id'], **result['sections'][mapping[stage]])


@app.errorhandler(RequestEntityTooLarge)
def rejected_size(_issue):
    return jsonify(code='PAYLOAD_TOO_LARGE', message='单据批次超过 1.5 MB'), 413


def main():
    parser = ArgumentParser(description=DISPLAY['title'])
    commands = parser.add_subparsers(dest='command', required=True)
    runner = commands.add_parser('evaluate', help='复算一个班次，并输出处置单与审计证据')
    runner.add_argument('--capacity', type=int, default=12)
    runner.add_argument('--strategy', choices=('balanced', 'focus'), default='balanced')
    runner.add_argument('--input', type=Path)
    runner.add_argument('--output', type=Path)
    server = commands.add_parser('serve', help='打开本地工作台')
    server.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if args.command == 'serve':
        from waitress import serve
        sample()
        serve(app, host='0.0.0.0', port=args.port, threads=4)
        return
    try:
        capacity, strategy = validate_parameters(args.capacity, args.strategy)
        if args.input:
            custom = open_fixture(args.input)
            result = execute(custom['records'], capacity, strategy, as_of=custom.get('as_of', 96))
        else:
            result = sample(capacity, strategy)
    except (ValueError, OSError) as issue:
        parser.error(str(issue))
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(output, encoding='utf-8')
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
