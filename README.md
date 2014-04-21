# Heroku CDN

This example uses the Google Drive SDK, Heroku and mongolab.

In order to run this example app, you'll need to set up a Google Drive SDK and deploy the app
to a public server. Below we outline how to do so using free accounts from Heroku and MongoLabs.

## Set up Heroku

We assume you're familiar with Git and have it installed.

  1. Visit http://www.heroku.com and sign up.
  2. Download the Heroku command line toolbelt from http://toolbelt.herokuapp.com/
  3. From your command line, type `heroku login` and enter your account details.
  4. Change to the server-side subdirectory of this example.
  5. Set up a git repository:

        $ git init

  6. Create a new app on Heroku:

        heroku create --stack cedar

    Note the URL of your live app.

## Set up Google Drive API

  1. Visit code.google.com/apis/console and create new project.
  2. On API section turn on 'Drive API' and 'Drive SDK'
  3. On 'Credentials' section create new client ID (web application)
  4. 'Redirect URI' should be `<URL of your live app>/auth`
  5. Download JSON and put this file to directory of this example (rename this file to 'secrets.json')

## Set up MongoDB

  1. Visit https://mongolab.com and sign up.
  2. In the 'Databases' section, click 'Add'.
  3. Select the 'Free' plan on Amazon EC2, pick a database name, username and password.
  4. Click on your new database and note the connection URL. It should look something like this:

        mongodb://<user>:<password>@ds029807.mongolab.com:29807/<databaseName>

  5. Copy this URL to `MONGO_CONNECTION_STRING` variable in drive.py file


## Build and Deploy your app

  1. Run the following git commands:

        $ git add .
        $ git commit -m "Initial commit"
        $ git push heroku master

  2. Auth you Google Drive account on `<your live Heroku URL>/auth`

## Check your app

You can upload file to `<your live Heroku URL>/upload`, in responce server return live file URL.
