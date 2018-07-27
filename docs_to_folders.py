from __future__ import print_function
import requests
import click
import os
from lxml import etree

with open('secure.txt', 'r') as f:
	secure = dict()
	for line in f:
		key, value = line.split(':')
		secure[key] = value

options_string = '[-c <case name>] [-n <number of documents] [-h <host name>]'
@click.command(options_metavar=options_string)
@click.option('-p', '--port', default='#', metavar='<port number>')
@click.option('-u', '--user-name', default='#', metavar='<user name>')
@click.option('-w', '--password', default='#', metavar='<')
@click.option('-h', '--host', is_eager=True, metavar='<host name>')
@click.option('-c', '--case', is_eager=True, metavar='<case name>')
@click.option('-d', '--doc-count', is_eager=True, metavar='<docs per folder>')
@click.option('-f', '--folder-count', is_eager=True, metavar='<folder count>')
def sample_folders(case, number_of_documents, host):
	pass