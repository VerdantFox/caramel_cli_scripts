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
@click.option('-p', '--port', default=secure['port'], envvar='CARAMEL_PORT', metavar='<port number>')
@click.option('-u', '--user-name', default=secure['username'], envvar='CARAMEL_USERNAME', metavar='<user name>')
@click.option('-w', '--password', default=secure['password'], envvar='CARAMEL_PASSWORD', metavar='<password>')
def check_folders(port, user_name, password, host, cases):
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
		for folder in folders:
			folder_id = folder.get('uri').split('/')[-1]
			get_url = 'http://{host}:{port}/case/{case}/folder/{folder_id}/b'.format(
				host=host, port=port, case=case, folder_id=folder_id)
			get_request = requests.get(url=get_url, auth=auth,
			                           params={'facets': 'doc.id(count;limit=10000000)&maxhits=0'})
			current_doc_count = int(etree.fromstring(get_request.text).findall('.//count')[0].text)
			print("case: {case}, folder id: {folder_id}, document count: {current_doc_count}".format(
				case=case, folder_id=folder_id, current_doc_count=current_doc_count))


if __name__ == "__main__":
	check_folders()
