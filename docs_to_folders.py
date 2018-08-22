"""Add documents to cases' folders in multi-threaded fashion

Add specified number of random documents to specified cases using caramel
'sample' method. Recommend using ~30 total threads. I.e. if running 3 instances
of this script (one per case) do run 10 threads each. 15 threads for 2 cases,
30 threads for one case.

Options/args:
-c --cases CASES [required]
    comma separated list of cases to check folder counts for
    example case1,case2,case3,etc...
-d --doc-count DOC_COUNT
    document count desired in folders
-h --host HOST[required]
    server host to check folder counts for
-p --port PORT
    port for checking counts
-u --user-name USERNAME
    username for authentication
-w --password PASSWORD
    password for authentication
-t --thread-count (flag)
    number of threads used to add documents to folders
--purge (flag)
    will purge all documents from folders before adding new documents
"""
from __future__ import print_function, division
import requests
import click
from lxml import etree
import time
import threading
import sys


with open('secure.txt', 'r') as f:
    secure = dict()
    for line in f:
        if line != '' and line != '\n':
            key, value = line.strip('\n').split(':')
            secure[key] = value

options_string = '[-c <case names (comma separated if multiple)>] [-d <number of documents>] [-h <host name>]' \
                 '[-p <port number>] [-u <user name>] [-w <password>] [-t <threads>] [--purge]'
glob_vars = {}


@click.command(options_metavar=options_string)
@click.option('-c', '--cases', required=True, metavar='<case names (comma separated if multiple)>')
@click.option('-d', '--doc-count', type=click.INT, required=True, metavar='<docs per folder>')
@click.option('-h', '--host', required=True, envvar='CARAMEL_HOST', metavar='<host name>')
@click.option('-p', '--port', type=click.INT, default=secure['port'], envvar='CARAMEL_PORT', metavar='<port number>')
@click.option('-u', '--user-name', default=secure['username'], envvar='CARAMEL_USERNAME', metavar='<user name>')
@click.option('-w', '--password', default=secure['password'], envvar='CARAMEL_PASSWORD', metavar='<password>')
@click.option('-t', '--thread-count', type=click.INT, default=10, metavar='<thread count>')
@click.option('--purge', 'purge', is_flag=True)
def sample_folders(cases,  doc_count, host, port, user_name, password, thread_count, purge):
    """Adds specified number of random documents from cases to folders using Caramel 'sample' method"""
    glob_vars['auth'] = (user_name, password)
    glob_vars['host'] = host
    glob_vars['port'] = port
    glob_vars['purge'] = purge
    glob_vars['doc_count'] = doc_count
    if doc_count <= 0:
        raise click.BadParameter("doc_count must be an integer greater than 0")
    if not 1 <= thread_count <= 100:
        raise click.BadParameter("thread count must be a number between 1 and 100")

    cases = cases.strip(',').split(',')
    click.echo("Host name: {}".format(host))
    click.echo("Port number: {}".format(port))
    click.echo("User name: {}".format(user_name))
    click.echo("Plan to bring folders in case(s) to within 98% ({doc_98}) of {doc_count} random documents".format(
        doc_98=glob_vars['doc_count'] * 0.98, doc_count=glob_vars['doc_count']))

    for case in cases:
        folder_feed = 'http://{host}:{port}/case/{case}/folder'.format(host=host, port=port, case=case)
        try:
            r = requests.get(url=folder_feed, auth=glob_vars['auth'], params={'maxhits': '10000'})
        except requests.exceptions.ConnectionError:
            raise click.BadParameter("Host name not recognized!")
        if r.status_code == 200:
            pass  # Success
        elif r.status_code == 404:
            raise click.BadParameter("Case '{}' could not be found. Check case name's spelling.".format(case))
        elif r.status_code == 401:
            raise click.BadParameter("Unauthorized -- invalid login credentials. Check username and password.")
        else:
            raise click.BadParameter("Something went wrong. \nGot the following status code: '{code}'. "
                                     "\nThe following headers were produced: '{headers}'".format(
                                                        code=r.status_code, headers=r.headers))
        docs_url = 'http://{host}:{port}/case/{case}/document'.format(
            host=host, port=port, case=case)
        docs_params = {'uhits': '1', 'maxhits': '0'}
        doc_resp = requests.get(url=docs_url, auth=glob_vars['auth'], params=docs_params)
        case_doc_count = int(etree.fromstring(doc_resp.text).findall('.//unfiltered_hits')[0].text)
        folder_count = len(etree.fromstring(r.text).findall('.//folder'))
        click.echo("Working on '{case}':\n"
                   "\tcontains {case_doc_count} documents\n"
                   "\tcontains {folder_count} folders.".format(
                        folder_count=folder_count, case=case, case_doc_count=case_doc_count))

        if case_doc_count < glob_vars['doc_count']:
            sys.exit("Error:\tNot enough case documents to add to folders!\n"
                     "\tNeed: {doc_count} case documents for your request\n"
                     "\tHave: {case_doc_count} case documents\n\tExiting...".format(
                            doc_count=glob_vars['doc_count'], case_doc_count=case_doc_count))

        glob_vars['max_threads'] = threading.BoundedSemaphore(thread_count)

        with click.progressbar(etree.fromstring(r.text).findall('.//folder'),
                               label="Adding up to {} documents to each folder".format(doc_count)) as folders:
            for folder in folders:
                glob_vars['max_threads'].acquire(blocking=True)
                t = threading.Thread(target=add_docs_to_folder,
                                     args=(case, folder))
                t.start()


def add_docs_to_folder(case, folder):
    """Add specific number of documents to a folder in multi-threaded fashion"""
    folder_id = folder.get('uri').split('/')[-1]
    get_url = 'http://{host}:{port}/case/{case}/folder/{folder_id}/b'.format(
        host=glob_vars['host'], port=glob_vars['port'], case=case, folder_id=folder_id)
    get_params = {'facets': 'doc.id(count;limit=10000000)', 'maxhits': '0'}
    purge_url = 'http://{host}:{port}/case/{case}/folder/{folder_id}'.format(
        host=glob_vars['host'], port=glob_vars['port'], case=case, folder_id=folder_id)
    purge_headers = {'content-type': 'application/x-www-form-urlencoded'}
    purge_data = {'_method': 'purge'}

    if glob_vars['purge']:
        current_doc_count = get_doc_count(case, folder_id)
        if current_doc_count > glob_vars['doc_count']:
            purge_resp = requests.post(
                url=purge_url, auth=glob_vars['auth'], headers=purge_headers, data=purge_data)
            get_attempts = 0
            while current_doc_count != 0:
                get_attempts += 1
                time.sleep(0.5)
                get_resp = requests.get(url=get_url, auth=glob_vars['auth'],
                                        params=get_params)
                current_doc_count = int(etree.fromstring(
                    get_resp.text).findall('.//count')[0].text)
                if get_attempts > 24:   # 12 seconds
                    break

    while_passes = 0
    get_attempts = 0
    previous_doc_count = None
    while True:
        current_doc_count = get_doc_count(case, folder_id)
        get_attempts += 1
        # Sometimes takes a few seconds after POST for database update to show in GET
        if while_passes != 0 and get_attempts < 11:
            if previous_doc_count == current_doc_count:
                time.sleep(1)
                continue
        if current_doc_count < glob_vars['doc_count']:
            docs_to_add = glob_vars['doc_count'] - current_doc_count
        else:
            break
        # Escape valve for not having to exactly hit doc count.
        # Sometimes sample will choose docs for folder that were already there.
        if (current_doc_count / glob_vars['doc_count']) > 0.98:
            break
        if docs_to_add > 0:
            if docs_to_add / 10000 <= 1:
                add_docs = docs_to_add
            else:
                add_docs = 10000
            post_url = 'http://{host}:{port}/case/{case}/folder/{folder}'.format(
                host=glob_vars['host'], port=glob_vars['port'], case=case, folder=folder_id)
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            data = {'_method': 'sample', 'target_count': add_docs}
            post_resp = requests.post(url=post_url, auth=glob_vars['auth'],
                                      headers=headers, data=data)
            previous_doc_count = current_doc_count
        get_attempts = 0
        while_passes += 1
    glob_vars['max_threads'].release()
    return


def get_doc_count(case, folder_id):
    """Get the number of documents in folder"""
    get_url = 'http://{host}:{port}/case/{case}/folder/{folder_id}/b'.format(
        host=glob_vars['host'], port=glob_vars['port'], case=case, folder_id=folder_id)
    get_params = {'facets': 'doc.id(count;limit=10000000)', 'maxhits': '0'}
    get_resp = requests.get(url=get_url, auth=glob_vars['auth'],
                            params=get_params)
    current_doc_count = int(etree.fromstring(get_resp.text).findall('.//count')[0].text)
    return current_doc_count


if __name__ == '__main__':
    sample_folders()
