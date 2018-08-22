"""Delete up to 10,000 folders from specified cases in multi-threaded fashion

Delete folders using DELETE directed at a folder URI.
Note: this process seems to be intensive on host. From testing I found that
performance maxes out at ~ 3 total threads. Recommend running ~3 total
threads spread across however many instances of this script that are running.
I.e. 3 threads on 1 process or 1 thread each on 3 processes.

Options/args:
-c --cases CASES [required]
    comma separated list of cases to check folder counts for
    example case1,case2,case3,etc...
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
"""
from __future__ import print_function, division
import requests
import click
from lxml import etree
import threading


with open('secure.txt', 'r') as f:
    secure = dict()
    for line in f:
        if line != '' and line != '\n':
            key, value = line.strip('\n').split(':')
            secure[key] = value

options_string = '[-c <case names (comma separated if multiple)>] [-h <host name>]' \
                 '[-p <port number>] [-u <user name>] [-w <password>] [-t <threads>]'
glob_vars = {}


@click.command(options_metavar=options_string)
@click.option('-c', '--cases', required=True, metavar='<case names (comma separated if multiple)>')
@click.option('-h', '--host', required=True, envvar='CARAMEL_HOST', metavar='<host name>')
@click.option('-p', '--port', type=click.INT, default=secure['port'], envvar='CARAMEL_PORT', metavar='<port number>')
@click.option('-u', '--user-name', default=secure['username'], envvar='CARAMEL_USERNAME', metavar='<user name>')
@click.option('-w', '--password', default=secure['password'], envvar='CARAMEL_PASSWORD', metavar='<password>')
@click.option('-t', '--thread-count', type=click.INT, default=1, metavar='<thread count>')
def traverse_folders(cases, host, port, user_name, password, thread_count):
    """Delete all folders (up to 10,000) in specified case.

    Recommend 3 TOTAL threads (spread across however many processes).
    """
    glob_vars['auth'] = (user_name, password)
    glob_vars['host'] = host
    glob_vars['port'] = port
    thread_count = thread_count
    if not 1 <= thread_count <= 100:
        raise click.BadParameter("thread count must be a number between 1 and 100")

    cases = cases.strip(',').split(',')
    click.echo("Host name: {}".format(host))
    click.echo("Port number: {}".format(port))
    click.echo("User name: {}".format(user_name))

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
        folder_count = len(etree.fromstring(r.text).findall('.//folder'))
        click.echo("Working on '{case}':\n"
                   "\tcontains {folder_count} folders (limit 10,000).".format(
                        folder_count=folder_count, case=case))
        glob_vars['max_threads'] = threading.BoundedSemaphore(thread_count)

        with click.progressbar(etree.fromstring(r.text).findall('.//folder'),
                               label="Deleting folders...") as folders:
            for folder in folders:
                glob_vars['max_threads'].acquire(blocking=True)
                t = threading.Thread(target=delete_folder,
                                     args=(case, folder))
                t.start()


def delete_folder(case, folder):
    """Add specific number of documents to a folder in multi-threaded fashion"""
    folder_id = folder.get('uri').split('/')[-1]
    delete_uri = '/case/{case}/folder/{folder_id}'.format(
         case=case, folder_id=folder_id)
    delete_url = 'http://{host}:{port}{delete_uri}'.format(
        host=glob_vars['host'], port=glob_vars['port'], delete_uri=delete_uri)
    del_resp = requests.delete(url=delete_url, auth=glob_vars['auth'])
    if del_resp.status_code != 200:
        click.echo("Error deleting folder at: {delete_uri}".format(
            delete_uri=delete_uri))
    glob_vars['max_threads'].release()
    return


if __name__ == '__main__':
    traverse_folders()
