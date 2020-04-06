# The Existential Risk Research Assessment (TERRA)
The **Existential Risk Research Assessment (TERRA)** application uses crowdsourcing and machine learning to help produce an open-access bibliography of publications about existential risk and global catastrophic risk.

## Setting up TERRA software

### Google reCAPTCHA
The TERRA system uses **Google reCAPTCHA** to prevent spam form submissions. To set up **Google reCAPTCHA** for the website domain that will host your TERRA application, go to:  

https://www.google.com/recaptcha/  

This will provide you with a `reCAPTCHA Site Key` and a `reCAPTCHA Secret Key` for your domain. Copy both text strings into a temporary text file, ready for input during the setup process.

### SMTP account for bulk mailing
The TERRA system is designed to send bulk emails to remote assessors to notify them that there are new publications to be assessed. To send bulk email mailings from the TERRA system, you will need an SMTP email account that does not block bulk mailings. 

Google's free **Gmail** service allows up to 500 emails to be sent during a 24-hour period, though you will need to decrease Gmail's security to allow SMTP access to work - google `send gmail smtp security settings` for more information.

### Information required during setup
The following information will be required during setup:

- *Domain name of website*: The domain name of your TERRA website, ie. where your application will be accessible from.

- *Domain name of email host*: The domain name of the SMTP server that will be used to send outbound emails.

- *SMTP port of email host*: The SMTP port of the email host. For Gmail, this will be 587.

- *Email host username*: The username for logging into SMTP server.

- *Email host password*: The password for logging into the SMTP server.

- *Default from email address*: The email address to send all outbound email messages from.

- *Send to test email address*: During the setup phase, a test email will be sent to this address.

- *Google reCAPTCHA SITE key*
- *Google reCAPTCHA SECRET key*

- *Elsevier API Key* and *Elsevier Institution Token*: These are required to download text content from Elsevier's Scopus(R) text library. To obtain an `API Key` and `Institution Token`, contact Elsevier at https://dev.elsevier.com/index.html  
Note that at the time of writing, Elsevier's self-service API key only provides access to article titles and not full article abstracts.

- *Name of new MySQL database to be used for TERRA system*: For example `xrisk`. The database must not already exist.

- *Name of new MySQL database user to be used in application*: For example `xriskuser`. The user must not already exist.

- *Password for new user*

- *Root password for logging into MySQL*

- *Path for MySQL backups*: This could be the path to an AWS S3 or Google Bucket storage container.

Collect all of this information above before starting the software installation process.

### Install core software
Install `MySQL`, `Pip`, `Python3`, `Git`, `virtualenv` and `Apache2` on your target server:
```
sudo apt update
sudo apt install mysql-server python-pip libmysqlclient-dev python3 python3-dev python3-mysqldb git virtualenv libexpat1 apache2 apache2-utils ssl-cert libapache2-mod-wsgi-py3
```

Ensure MySQL can be accessed as `root` user through the command line by typing:

```
sudo mysql_secure_installation
sudo mysql
```
Then in `mysql` prompt, enter:

```
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '[your_root_password]';
```

### MySQL time zone tables
Load time zone tables into MySQL using the `mysql_tzinfo_to_sql`:
```
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -uroot -p mysql
```
For more information on using `mysql_tzinfo_to_sql`, go to:  

https://dev.mysql.com/doc/refman/8.0/en/mysql-tzinfo-to-sql.html


### Install TERRA software
Install the source code for TERRA by typing:

```
git clone https://github.com/x-risk/x-risk.git
```

Create a virtual environment for Python3 by typing:

```
cd x-risk
which python3
virtualenv -p [insert_path_from_previous_prompt] venv
source venv/bin/activate
```

Run `setup.sh` and enter all the details gathered during the `Information required during setup` stage, above:

```
./setup.sh
```

The setup process will send a test email, create the relevant database and database user and output two configuration files `/path/to/x-risk/config.py` and `/path/to/x-risk/config.json`. To modify most settings, edit `/path/to/x-risk/config.py`.

Once the setup process finishes, you can check the application is working by going to:
```
./manage.py runserver
```
Open a web browser and load the application (development not production environment) at:
```
http://127.0.0.1:8000
```

Some elements of the system requires data to be present for the `engine.publication`, `engine.topic`, and `engine.publication_search_topics` models. To load dummy data into these models, enter:
```
./manage.py loaddata dummydata.json
```

You can delete or edit this data at any point by logging into the Django admin system at `/admin` using your superuser account.

## Updating index
Whenever new publications are added to the database, it will be necessary to update the search index. You can do this by setting up a **cron job** to update the index (see "CRON jobs for managing regular tasks", below) or by typing:
```
./manage.py update_index
```
If you are deploying TERRA on Apache, you may need to set permissions on the search index folder so the web-server user can access it:
```
sudo chown -R [WEBSERVER-USER]:[WEBSERVER-GROUP] xrisk/whoosh_index
```
To find your `WEBSERVER-USER/GROUP` on Apache, type `apachectl -S`.

## Enable webserver access to media folder
You will need to give the webserver access to the **media** folder in order to upload content:  
```
sudo chown -R [WEBSERVER-USER]:[WEBSERVER-GROUP] media
```
To find your `WEBSERVER-USER/GROUP` on Apache, type `apachectl -S`.

## Testing email alerts
The TERRA system is designed to send monthly emails to subscribers with details of new publications. The monthly emails are sent using a `cron job` (see **Cron jobs for managing regular tasks**, below). Before setting up the `cron job`, it is recommended you send a test email to the *Default from email address* (entered during setup) to check the email system is working as it should and all email links are functioning correctly.  

To send a sample alert email to the *Default from email address*, enter:
```
./sendsamplealert.sh
```

## Deploying TERRA
For information on deploying the TERRA application to Apache in a production environment, go to:

https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/modwsgi/

An example Apache `site.conf` file is as follows:

```
<VirtualHost *:80>

    ServerName www.yourdomain.com
    ServerAlias yourdomain.com
    
    Alias /static/ /path/to/x-risk/static/
    Alias /media/ /path/to/x-risk/media/

    <Directory /path/to/x-risk/static>
        Require all granted
    </Directory>

    WSGIScriptAlias / /path/to/x-risk/xrisk/wsgi.py
    WSGIDaemonProcess xrisk user=www-data group=www-data threads=5 home=/path/to/x-risk python-home=/path/to/x-risk/venv

    ErrorLog "/var/log/apache2/xrisk-error_log"
    CustomLog "/var/log/apache2/xrisk-access_log" common

    <directory /path/to/x-risk/>
        WSGIProcessGroup xrisk
        WSGIApplicationGroup %{GLOBAL}
        WSGIScriptReloading On
        Require all granted
    </directory>

</VirtualHost>
```

## Enabling HTTPS on web server
You should install a secure **SSL** certificate on your webserver to ensure all data exchange between your website and users is securely encrypted. The simplest way to do that is to install a **LetsEncrypt** SSL certificate. To install **LetsEncrypt**, follow the instructions at:

https://letsencrypt.org/

### Problems installing *LetsEncrypt* on Apache webserver
During the installation of **LetsEncrypt** with an Apache webserver, you may experience the following error:

```
Name duplicates previous WSGI daemon definition.
```

If so, edit your Apache virtual host `*.conf` file and comment out the following line:

```
# WSGIDaemonProcess...
```

Repeat the **LetsEncrypt** installation process. Once installation has completed, do the following:

#### Redit your existing virtual host file
Re-edit your virtual host `*.conf` file and uncomment the `WSGIDaemonProcess` line that you commented above. 

#### Edit new SSL virtual host file
Edit the `*-le-ssl.conf` that has been created by **LetsEncrypt** alongside your existing virtual host `*.conf` file:
- Uncomment the same `WSGIDaemonProcess` line as the existing `*.conf` file. 
- Add the prefix `ssl-` to the name of the `WSGIDaemonProcess` and `WSGIProcessGroup` first parameters. For example, if the line is `WSGIDaemonProcess xrisk`, change the `xrisk` parameter to `ssl-xrisk` so the file becomes:

```

WSGIDaemonProcess ssl-xrisk user=www-data group=www-data threads=5 home=/path/to/x-risk python-home=/path/to/x-risk/venv

ErrorLog "/var/log/apache2/xrisk-error_log"
CustomLog "/var/log/apache2/xrisk-access_log" common

<directory /path/to/x-risk/>
    WSGIProcessGroup ssl-xrisk
    WSGIApplicationGroup %{GLOBAL}
    WSGIScriptReloading On
    Require all granted
</directory>

```

#### Open HTTPS port on your webserver
If you are running a server on Google or AWS, ensure you have opened up the necessary firewall rules to allow access to HTTPS (port 443)

#### Edit config.py to redirect all HTTP requests to HTTPS
To ensure all non-secure (HTTP) page requests are redirected to your secure site (HTTPS), edit your `config.py` file within your `x-risk` project and set the `SECURE_SSL_REDIRECT` parameter to `True`:
```
SECURE_SSL_REDIRECT=True
```
Restart your Apache webserver to load all changes. When you reload your existing website, you should now be redirected to a secure version of your website.


## Cron jobs for managing regular tasks
The TERRA system uses a daily cron job and two monthly cron jobs to carry out regular tasks like database backups, index maintenance, monthly downloads from Scopus, and monthly notifications to registered users. 

### Daily cron job
All daily tasks are contained in the script `cron_daily.sh`. You may need to modify the last line of this script to reflect your particular Apache or webserver user. It should read:
```
chown -R [WEBSERVER-USER]:[WEBSERVER-GROUP] $SCRIPTPATH/xrisk/whoosh_index
```
To find your `WEBSERVER-USER/GROUP` on Apache, type `apachectl -S`

To install this cron job, type `sudo crontab -e` and enter the following, replacing `/path/to/x-risk/` with the path to your TERRA application source code:

```
@daily /path/to/x-risk/cron_daily.sh 2>&1 | /path/to/x-risk/timestamp.sh >> /path/to/x-risk/cron.log
```
It is recommended all TERRA cronjobs are run under the root user (hence `sudo crontab -e`) to mitigate possible file permission issues.

If you are using a Google Bucket to store database backups and are experiencing permission errors, you may need to supply the name of your Google Bucket authorized user. Comment out the following line in `cron_daily.sh`:
```
eval "cp $SCRIPTPATH/$MYSQLDUMPFILE $DB_BACKUPDIR/$MYSQLDUMPFILE"
```
and uncomment:
```
su - [google_bucket_user] -c "cp $SCRIPTPATH/$MYSQLDUMPFILE $DB_BACKUPDIR/$MYSQLDUMPFILE"
```
Replacing `[google_bucket_user]` with the the system user you used to mount the bucket.

### Monthly cron jobs
The monthly tasks are contained in two scripts: `cron_monthly.sh` and `cron_monthly_alerts.sh`. The `cron_monthly.sh` script retrieves and processes data from the Scopus text library while the `cron_monthly_alerts.sh` sends out alerts to the system's mailing list.

**WARNING: The `cron_monthly_alerts.sh` script will email everybody on the mailing list - it should only be run as a scheduled monthly cron job**

To install these scripts as cronjobs, type `sudo crontab -e` and enter the following, replacing `/path/to/x-risk/` with the path to your TERRA application source code:

```
0 6 28 * * /path/to/x-risk/cron_monthly.sh 2>&1 | /path/to/x-risk/timestamp.sh >> /path/to/x-risk/cron.log

0 18 28 * * /path/to/x-risk/cron_monthly_alerts.sh 2>&1 | /path/to/x-risk/timestamp.sh >> /path/to/x-risk/cron.log
```
`0 6 28 * *` = 6am on the 28th day of the month  
`0 18 28 * *` = 6pm on the 28th day of the month

## X-Risk Content Management System 

The TERRA system comes bundled with a **Content Management System (CMS)** containing several content pages to deliver a fully working and user-friendly website out of the box. 

For more information about using the **X-Risk Content Management System**, go to:  

https://github.com/x-risk/x-risk/tree/master/contentmanager  

## Copyright

TERRA Application  
Copright (c) 2018 Gorm Shackleford  
Released under MIT License

Material Kit Template  
Copyright (c) 2017 Creative Tim  
Released under MIT License  
https://www.creative-tim.com/product/material-kit

Bootstrap-Select  
Copyright (c) 2012-2018 SnapAppointments, LLC  
Released under MIT License  
https://developer.snapappointments.com/bootstrap-select/
