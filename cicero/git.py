import os
import flask
import sys
import requests
import json

if sys.version_info[0] > 2:
    from urllib import request
    _urlopen = request.urlopen
else:
    import urllib2
    _urlopen = urllib2.urlopen

blueprint = flask.Blueprint('git', __name__)

URL_BASE = 'CICERO_URL_BASE_is_undefined'
_url_base = os.environ.get('CICERO_URL_BASE')
if _url_base is not None:
    URL_BASE = _url_base


def get_sha_github(owner, repo, ref):
    uri = 'https://api.github.com/repos/{0}/{1}/commits/{2}'.format(owner, repo, ref)
    try:
        response = requests.get(uri)
    except requests.ConnectionError:
        return "Connection Error"
    data = json.loads(response.text)
    return data['sha']


def test_get_sha_github():
    sha = get_sha_github('bast', 'cicero', 'bfa3748447')
    assert sha == 'bfa3748447fe0c7455f19a027575406a0c561a4f'


def set_url_base(host, port):
    global URL_BASE
    URL_BASE = 'http://{}:{}'.format(host, port)


@blueprint.route('/')
def home():
    return flask.render_template('index.html', url_base=URL_BASE)


def render_github_markdown(path):
    from .title import extract_title
    from .images import fix_images

    (owner, repo, _ref) = path.split('/')[0:3]
    file_path = '/'.join(path.split('/')[3:])

    # we need to translate the reference to a sha (the reference can be a sha)
    # the reason for this is that cdn.rawgit.com caches files forever
    # the reference may change but the sha won't
    sha = get_sha_github(owner, repo, _ref)

    root = '{0}/{1}/{2}/'.format(owner, repo, sha)
    if '/' in file_path:
        root += '/'.join(file_path.split('/')[:-1]) + '/'
        last_file = file_path.split('/')[-1]
    else:
        last_file = file_path

    prefix = 'https://cdn.rawgit.com/{0}'.format(root)

    try:
        url = prefix + '/' + last_file

        response = _urlopen(url)

        markdown = response.read().decode("utf-8")
        if markdown == 'Not Found':
            return flask.render_template('404.html')

        title = extract_title(markdown)
        style = flask.request.args.get('style')
        if style is None:
            style = 'default'

        try:
            url = prefix + '/' + 'remark.html'
            response = _urlopen(url)
            template = response.read().decode("utf-8")
            return flask.render_template_string(template,
                                                title=title,
                                                markdown=fix_images(markdown, prefix),
                                                style=style)
        except IOError:
            return flask.render_template('remark.html',
                                         title=title,
                                         markdown=fix_images(markdown, prefix),
                                         style=style)
    except IOError:
        return flask.render_template('404.html')


@blueprint.route('/v1/github/<path:path>/remark/')
def render_v1(path):
    return render_github_markdown(path)


@blueprint.route('/v2/remark/github/<path:path>/')
def render_v2(path):
    return render_github_markdown(path)
