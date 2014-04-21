#!/usr/bin/env python
# -*- coding: utf-8 -*-


__version__ = '0.01'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2014'


import os
from functools import wraps
from flask import Flask, Response, json, request, stream_with_context, redirect
from pymongo import MongoClient
import urllib2

from drive import GoogleDriveUploader, CodeExchangeException, NoUserIdException

app = Flask(__name__)
gdu = GoogleDriveUploader()
db = gdu.getDB()



def check_auth(username, password):
	"""
		This function is called to check if a username /
		password combination is valid.
	"""
	return username == 'admin' and password == 'secret'

def authenticate():
	"""Sends a 401 response that enables basic auth"""
	return Response(
		'Could not verify your access level for that URL.\n'
		'You have to login with proper credentials', 401,
		{'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		if not auth or not check_auth(auth.username, auth.password):
			return authenticate()
		return f(*args, **kwargs)
	return decorated



@app.route('/')
def index():
	return request.url_root

@app.route('/auth')
@requires_auth
def auth():
	try:
		#t = GoogleDriveUploader()
		gdu.gdrive_redirect_uri = request.url_root + 'auth'
		c = gdu.getCredentials(authorization_code=request.args.get('code', None))
		user = gdu.getUserInfo()
	except CodeExchangeException, e:
		return redirect(e.authorization_url, code=302)
	except NoUserIdException, e:
		return 'User error'
	return Response(json.dumps(user), status=200, mimetype='application/json')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
	rv = { 'result': 'error', 'message': 'Url param missed.' }
	out = None
	if request.method == 'POST':
		url = request.form.get('url', False)
		if url:
			try:
				out = gdu.upload(url)
			except CodeExchangeException:
				rv['message'] = 'Unauthorized in gdrive.'
				out = None
		elif request.files.get('file', False):
			f = request.files.get('file')
			try:
				out = gdu.uploadFromMemory(f.stream.read(),
						title=f.filename,
						mimetype=f.content_type)
			except CodeExchangeException:
				rv['message'] = 'Unauthorized in gdrive.'
				out = None
	else:
		url = request.args.get('url', False)
		try:
			out = gdu.upload(url)
		except CodeExchangeException:
			rv['message'] = 'Unauthorized in gdrive.'
			out = None
	if out is not None:
		rv = {
			'result': 'ok',
			'aURL': out.get('webContentLink')
		}
		rv['url'] = request.url_root + 'get/' + out.get('id', 'error') + '/' + out.get('title')
		db_record = {
			'gdid': out.get('id'),
			'url': out.get('webContentLink'),
			'mimetype': out.get('mimeType'),
		}
		db.files.insert(db_record)
	return Response(json.dumps(rv), status=200, mimetype='application/json')

@app.route('/get/<gdid>/<filename>')
def get(gdid, filename):
	if gdid is not 'error':
		f = db.files.find_one({ 'gdid': gdid })
		if f:
			f['hits'] = f.get('hits', 0) + 1
			db.files.save(f)
			url = f.get('url')
			if url:
				req = urllib2.Request(url)
				page = urllib2.urlopen(req)
				return Response(stream_with_context(page), status=page.code, mimetype=page.headers['Content-Type'])
	return Response(json.dumps({ 'result': 'error' }), status=200, mimetype='application/json')


if __name__ == "__main__":
	app.debug = True
	app.run()
