"""Lists document count of every folder in case.

Can specify an expected doc count,
in which case script will only display the document count of folders that are not
within 3% of the expected document count. Useful for determining if docs_to_folders
correctly added the specified number of documents to folders.

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
-d --doc-count DOC_COUNT
    expected document count
"""
from __future__ import print_function, division
import requests
import click
from lxml import etree

with open('secure.txt', 'r') as f:
    secure = dict()
    for line in f:
        if line != '' and line != '\n':
            key, value = line.strip('\n').split(':')
            secure[key] = value

options_string = '[-c <case names (comma separated if multiple)>] [-h <host name>]' \
                 '[-p <port number>] [-u <user name>] [-w <password>]'


@click.command(options_metavar=options_string)
@click.option('-c', '--cases', required=True, metavar='<case names (comma separated if multiple)>')
@click.option('-h', '--host', required=True, envvar='CARAMEL_HOST', metavar='<host name>')
@click.option('-p', '--port', type=click.INT, default=secure['port'], envvar='CARAMEL_PORT', metavar='<port number>')
@click.option('-u', '--user-name', default=secure['username'], envvar='CARAMEL_USERNAME', metavar='<user name>')
@click.option('-w', '--password', default=secure['password'], envvar='CARAMEL_PASSWORD', metavar='<password>')
@click.option('-d', '--doc-count', type=click.INT, default=None, metavar='<expected doc count>')
def check_folders(port, user_name, password, host, cases, doc_count):
    """Checks folders' document counts"""
    auth = (user_name, password)
    cases = cases.strip(',').split(',')
    click.echo("Host name: {}".format(host))
    click.echo("Port number: {}".format(port))
    click.echo("User name: {}".format(user_name))

    for case in cases:
        folder_feed = 'http://{host}:{port}/case/{case}/folder'.format(host=host, port=port, case=case)
        r = requests.get(folder_feed, auth=auth, params={'maxhits': '10000'})
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
        click.echo("Working on '{case}': contains {folder_count} folders.".format(
            case=case, folder_count=folder_count))
        folders = etree.fromstring(r.text).findall('.//folder')
        if doc_count is not None:
            click.echo("Will print documents that aren't within 3% of specified doc count...")
        for folder in folders:
            folder_id = folder.get('uri').split('/')[-1]
            get_url = 'http://{host}:{port}/case/{case}/folder/{folder_id}/b'.format(
                host=host, port=port, case=case, folder_id=folder_id)
            get_request = requests.get(url=get_url, auth=auth,
                                       params={'facets': 'doc.id(count;limit=10000000)&maxhits=0'})
            current_doc_count = int(etree.fromstring(get_request.text).findall('.//count')[0].text)
            doc_count_string = "\tcase: {case}, folder id: {folder_id}, document count: {current_doc_count}".format(
                    case=case, folder_id=folder_id, current_doc_count=current_doc_count)
            if doc_count is not None:
                if doc_count * 0.97 < current_doc_count < doc_count * 1.03:
                    pass  # approximately correct doc count
                else:
                    click.echo(doc_count_string)
            else:
                click.echo(doc_count_string)
        click.echo("Done checking '{case}'!".format(case=case))


if __name__ == "__main__":
    check_folders()
