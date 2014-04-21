#!/usr/bin/python
# -*- coding: utf-8 -*-

import httplib2
import pprint
import urllib2

from apiclient.discovery import build
from apiclient.http import MediaFileUpload, MediaInMemoryUpload
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import OAuth2Credentials
from apiclient import errors
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import httplib2
from pymongo import MongoClient


# Path to client_secrets.json which should contain a JSON document such as:
#   {
#     "web": {
#       "client_id": "[[YOUR_CLIENT_ID]]",
#       "client_secret": "[[YOUR_CLIENT_SECRET]]",
#       "redirect_uris": [],
#       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#       "token_uri": "https://accounts.google.com/o/oauth2/token"
#     }
#   }
CLIENTSECRETS_LOCATION = 'secrets.json'
SCOPES = [
		'https://www.googleapis.com/auth/drive',
		'https://www.googleapis.com/auth/userinfo.email',
		'https://www.googleapis.com/auth/userinfo.profile',
		# Add other requested scopes.
]

class GetCredentialsException(Exception):
	"""Error raised when an error occurred while retrieving credentials.

	Attributes:
		authorization_url: Authorization URL to redirect the user to in order to
				               request offline access.
	"""

	def __init__(self, authorization_url):
		"""Construct a GetCredentialsException."""
		self.authorization_url = authorization_url


class CodeExchangeException(GetCredentialsException):
	"""Error raised when a code exchange has failed."""

class NoUserIdException(Exception):
	"""Error raised when no user ID could be retrieved."""



class GoogleDriveUploader(object):
	"""docstring for GoogleDriveUploader"""
	def __init__(self, db=None, gdrive_redirect_uri=None):
		super(GoogleDriveUploader, self).__init__()
		self._db = db
		self._credentials = None
		self._drive_service = None
		self._mongo_connection = 'mongodb://E5MTEzYW:ZDM4M2Q3M2IwZGQ1MzQ@ds047197.mongolab.com:47197/cdn'
		self.gdrive_redirect_uri = gdrive_redirect_uri

	def getDB(self):
		if self._db is None:
			db_name = self._mongo_connection.split('/')[-1]
			self._db = MongoClient(self._mongo_connection)[db_name]
		return self._db

	def exchange_code(self, authorization_code):
		"""Exchange an authorization code for OAuth 2.0 credentials.

		Args:
			authorization_code: Authorization code to exchange for OAuth 2.0
			credentials.
		Returns:
			oauth2client.client.OAuth2Credentials instance.
		Raises:
			CodeExchangeException: an error occurred.
		"""
		if authorization_code is None or self.gdrive_redirect_uri is None:
			raise CodeExchangeException(None)
		
		flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
		flow.redirect_uri = self.gdrive_redirect_uri
		
		#flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, SCOPES, self.gdrive_redirect_uri)
		try:
			credentials = flow.step2_exchange(authorization_code)
			return credentials
		except FlowExchangeError, error:
			raise CodeExchangeException(None)

	def get_authorization_url(self):
		"""Retrieve the authorization URL.

		Args:
			email_address: User's e-mail address.
			state: State for the authorization URL.
		Returns:
			Authorization URL to redirect the user to.
		"""
		
		flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
		flow.redirect_uri = self.gdrive_redirect_uri
		flow.params['access_type'] = 'offline'
		flow.params['approval_prompt'] = 'force'
		#flow.params['user_id'] = email_address
		#flow.params['state'] = state
		return flow.step1_get_authorize_url()

	def getCredentials(self, authorization_code=None):
		if self._credentials is None:
			db_settings = self.getDB().settings
			auth = db_settings.find_one({ 'gdrive_credentials': { "$exists": True } })
			if auth is not None:
				self._credentials = OAuth2Credentials.new_from_json(auth.get('gdrive_credentials'))
			else:
				auth = {}
			if self._credentials is not None and self._credentials.access_token_expired:
				self._credentials.refresh(httplib2.Http())
				auth['gdrive_credentials'] = self._credentials.to_json()
				db_settings.save(auth)
			if self._credentials is None:
				try:
					self._credentials = self.exchange_code(authorization_code)
				except CodeExchangeException, error:
					error.authorization_url = self.get_authorization_url()
					raise error

				auth['gdrive_credentials'] = self._credentials.to_json()
				db_settings.save(auth)
			#elif self._credentials.refresh_token is not None:
			#	auth['credentials'] = self._credentials.to_json()
			#	db_settings.save(auth)
		'''
		if self._credentials.access_token_expired:
			db_settings = self.getDB().settings
			auth = db_settings.find_one({ 'gdrive_credentials': { "$exists": True } })
			if auth is None:
				auth = {}
			self._credentials.refresh(httplib2.Http())
			auth['gdrive_credentials'] = self._credentials.to_json()
			db_settings.save(auth)
		'''
		return self._credentials

	def getUserInfo(self):
		"""Send a request to the UserInfo API to retrieve the user's information.

		Args:
			credentials: oauth2client.client.OAuth2Credentials instance to authorize the
				         request.
		Returns:
			User information as a dict.
		"""
		user_info_service = build(
				serviceName='oauth2', version='v2',
				http=self.getCredentials().authorize(httplib2.Http()))
		user_info = None
		try:
			user_info = user_info_service.userinfo().get().execute()
		except errors.HttpError, e:
			pass
		if user_info and user_info.get('id'):
			return user_info
		else:
			raise NoUserIdException()

	def getDriveService(self):
		if self._drive_service is None:
			http = httplib2.Http()
			http = self.getCredentials().authorize(http)
			self._drive_service = build('drive', 'v2', http=http)
		return self._drive_service

	def uploadFromMemory(self, buff, title=None, mimetype=None):
		#media_body = MediaFileUpload(file_path_or_url, mimetype='text/plain', resumable=True)
		#media_body = MediaIoBaseUpload(open(file_path_or_url), mimetype='image/plain', resumable=True)
		media_body = MediaInMemoryUpload(buff, mimetype=mimetype, resumable=True)
		#im = cStringIO.StringIO(page.read())
		#media_body = MediaIoBaseUpload(im, mimetype=page.headers['Content-Type'], resumable=True)
		body = {
			'title': title,
			'mimeType': mimetype
		}

		rv = None
		try:
			rv = self.getDriveService().files().insert(body=body, media_body=media_body).execute()
		except errors.HttpError, error:
			pass
		if rv:
			self.addSharePermision(rv.get('id'))
		return rv

	def upload(self, url):
		req = urllib2.Request(url)
		page = urllib2.urlopen(req)
		title = url.split('/')[-1]
		title = title.split('?')[0]
		title = urllib2.unquote(title.encode('utf-8')).decode('utf-8')
		return self.uploadFromMemory(page.read(),
				title=title,
				mimetype=page.headers['Content-Type'])

	def download(self, file_id):
		try:
			file_info = self.getDriveService().files().get(fileId=file_id).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			return None
		download_url = file_info.get('downloadUrl')
		if download_url:
			resp, content = self.getDriveService()._http.request(download_url)
			if resp.status == 200:
				return content
			else:
				#print 'An error occurred: %s' % resp
				return None
		else:
			# The file doesn't have any content stored on Drive.
			return None

	def addSharePermision(self, file_id):
		new_permission = {
			#'value': value,
			#'id': 'anyoneWithLink',
			'type': 'anyone',
			'withLink': True,
			'role': 'reader'
		}
		try:
			return self.getDriveService().permissions().insert(
					fileId=file_id, body=new_permission).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			pass
		return None

	def getPermissions(self, file_id):
		try:
			return self.getDriveService().permissions().list(fileId=file_id).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			pass
		return None


if __name__=='__main__':
	#pprint.pprint(GoogleDriveUploader().upload('drive.py'))
	pprint.pprint(GoogleDriveUploader().upload('http://www.barcodekanojo.com/profile_images/kanojo/2576048/1382482591/%D0%94%D0%B6%D0%B8%D0%BD.png?w=88&h=88&face=true'))
	#pprint.pprint(GoogleDriveUploader().getPermissions('0B-nxIpt4DE2TcldEQTFVMmV3c0U'))
