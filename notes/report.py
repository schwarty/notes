import sys
import os
import glob
import tarfile

from datetime import datetime

import shutil

pwd = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(pwd, 'externals')

from externals import tempita
from externals import markdown


def make_log(reports_dir, title):

    messages = []
    paths = []
    sorted_paths = sorted(glob.glob(
        os.path.join(reports_dir, '%s_*' % title, 'index.html')))
    for index_path in sorted_paths[::-1]:
        print index_path
        if os.path.split(index_path)[0].endswith('_log'):
            continue
        html = open(index_path, 'rb').read()
        m = html.split('<div class="well well-small">')[1].split('</div>')[0]
        messages.append(m)
        paths.append(os.path.join(
            '..', index_path.split(reports_dir)[1].strip('/')))

    template = tempita.Template.from_filename(
        os.path.join(pwd, 'templates', 'log_template.html'))

    html = template.substitute(index_paths=paths,
                               messages=messages,
                               title=title,
                               bootstrap='')

    out_dir = os.path.join(reports_dir, '%s_log' % title)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    with open(os.path.join(out_dir, 'index.html'), 'wb') as f:
        f.write(html)

        if os.path.exists(os.path.join(out_dir, 'bootstrap')):
            shutil.rmtree(os.path.join(out_dir, 'bootstrap'))
        shutil.copytree(os.path.join(pwd, 'bootstrap'),
                        os.path.join(out_dir, 'bootstrap'))


def make_report(path, input_dirs, labels=None, message=None,
                tarball=True, track=True):
    if labels is None:
        labels = {}

    title = os.path.split(path)[1]
    parent_link = os.path.join('..', '%s_log' % title, 'index.html')

    now = datetime.now()
    timestamp = datetime.strftime(now, '%Y%m%d_%H%M%S')
    out_dir = '%s_%s' % (path, timestamp)
    timestamp = datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    categories = [
        labels.get(os.path.basename(d), labels.get(os.path.basename(d)))
        for d in input_dirs]

    for label, images_dir in zip(categories, input_dirs):
        category_dir = os.path.join(out_dir, label)
        if not os.path.exists(category_dir):
                os.makedirs(category_dir)

        page_path, images = make_page(images_dir, label,
                                      categories, title, parent_link)

        for img in images:
            name = os.path.split(img)[1]
            src = os.path.join(images_dir, name)
            dest = os.path.join(category_dir, name)
            shutil.copyfile(src, dest)

        shutil.move(page_path,
                    os.path.join(out_dir, os.path.split(page_path)[1]))

    if os.path.exists(message):
        message = markdown.Markdown().convert(open(message, 'rb').read())
    else:
        message = markdown.Markdown().convert(message)

    template = tempita.Template.from_filename(
        os.path.join(pwd, 'templates', 'index_template.html'))

    html = template.substitute(categories=categories,
                               timestamp=timestamp,
                               title=title,
                               message=message,
                               parent_link=parent_link)

    with open(os.path.join(out_dir, 'index.html'), 'wb') as f:
        f.write(html)
        shutil.copytree(os.path.join(pwd, 'bootstrap'),
                        os.path.join(out_dir, 'bootstrap'))

    if tarball:
        make_tarball(out_dir)

    if track:
        make_log(os.path.split(out_dir)[0], title)


def make_page(images_dir, label=None, categories=None,
              title=None, parent_link='#'):
    """Creates a page on a single directory containing images.
    """

    png_files = [f for f in glob.glob(os.path.join(images_dir, '*.png'))]
    bootstrap = '%s/' % pwd if categories is None else ''

    if categories is not None:
        images = sorted([os.path.join(label, os.path.split(f)[1])
                         for f in png_files])
    else:
        images = sorted([os.path.split(f)[1] for f in png_files])

    sections = {}

    for img in images:
        section_id = os.path.split(img)[1].split('__', 1)[0]
        sections.setdefault(section_id, []).append(img)

    if categories is None:
        categories = [label]
    if title is None:
        title = 'report'

    template = tempita.HTMLTemplate.from_filename(
        os.path.join(pwd, 'templates', 'brain_template.html'))

    html = template.substitute(images=sections,
                               categories=categories,
                               label=label,
                               title=title,
                               bootstrap=bootstrap,
                               parent_link=parent_link)

    page_path = os.path.join(images_dir, '%s.html' % label)

    with open(page_path, 'wb') as f:
        f.write(html)

    return page_path, images


def make_tarball(directory):
    print 'Making tarball...'
    os.chdir(os.path.split(directory)[0])
    archive_name = os.path.split(directory)[1]
    with tarfile.open(name='%s.tar.gz' % archive_name, mode='w:gz') as tar:
        for dir_path, dir_names, file_names in os.walk(directory):
            dir_path = os.path.join(
                archive_name,
                dir_path.split(archive_name)[1].strip('/'))
            for f in file_names:
                f = os.path.join(dir_path, f.strip('/'))
                tar.add(f)
    os.chdir(pwd)


def parse_command_line():
    from optparse import OptionParser
    parser = OptionParser()

    parser.add_option("-l", "--labels", dest="labels",
                      help=("labels for input dirs follwing this format: "
                            "input_dir1:label1 input_dir2:label2"), )
    parser.add_option("-t", "--tarball",
                      action="store_true", dest="tarball", default=False,
                      help="Create a tarball in addition of the directory.")
    parser.add_option("-m", "--message", dest="message",
                      help="Message as str or path to a markdown file.", )

    (options, args) = parser.parse_args()

    print args

    report_path = args[0]
    input_dirs = [d.rstrip('/') for d in args[1:]]

    if options.labels is None:
        labels = {}
        for input_dir in input_dirs:
            dirname = os.path.split(input_dir)[1]
            labels[dirname] = raw_input('Label for %s: ' % dirname)
    else:
        labels = dict([l.split(':') for l in options.labels.split(' ')])

    if options.message is None:
        options.message = raw_input('Message: ')

    make_report(report_path,
                input_dirs=input_dirs,
                labels=labels,
                message=options.message,
                tarball=options.tarball)


if __name__ == '__main__':
    # directories = ['/home/ys218403/Data/brainpedia/report_maps',
    #                '/home/ys218403/Data/brainpedia/out_forward_inference',
    #                '/home/ys218403/Data/brainpedia/reverse_inference_figures']

    # labels = {'report_maps': 'maps',
    #           'report_design': 'design',
    #           'out_forward_inference': 'forward',
    #           'reverse_inference_figures': 'reverse', }

    # make_report('/home/ys218403/Data/brainpedia/snapshots/brainpedia',
    #             input_dirs=directories,
    #             labels=labels,
    #             message='## test\nthis is just a test message to see how it looks.',
    #             tarball=True)

    parse_command_line()

    # make_log(
    #     '/home/ys218403/Data/brainpedia/snapshots/brainpedia', 'brainpedia')
