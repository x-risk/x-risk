
# Script for setting up XRisk application
# Code snippets taken from internet and credited where relevant
# 2020

# Workaround for problem with bash on OSX not supporting -i flag on read
# https://stackoverflow.com/questions/22634065/bash-read-command-does-not-accept-i-parameter-on-mac-any-alternatives

function readinput() {
  local CLEAN_ARGS=""
  default=''
  prompt=''
  while [[ $# -gt 0 ]]; do
    local i="$1"
    case "$i" in
      "-i")
		default="$2"
        shift
        shift
        ;;
      "-p")
		prompt="$2"
        shift
        shift
        ;;
      *)
        input=$1
        shift
        ;;
    esac
  done
  read -p "$prompt [$default]: " tempinput
  eval $input="${tempinput:-$default}" 
}


readinput -e -p "Domain name to be used" -i "localhost" domain
echo "Website will be run on ${domain}"

readinput -e -p "Domain name of email host" -i "127.0.0.1" email_host
readinput -e -p "SMTP port of email host (use 587 for Gmail)" -i "25" email_port
readinput -e -p "Email host username" -i "your_username" email_username
read -p "Email host password (Note: password will be hidden): " -s email_password; echo
readinput -e -p "Default from email" -i "your_email_address" email_default_from
readinput -e -p "Send test email to" -i "test_email_address" email_test_to

TESTEMAIL_RESPONSE="$(python testemail.py $email_default_from $email_test_to $email_host -n $email_port -u $email_username -p$email_password -t)"

if [ "$TESTEMAIL_RESPONSE" != "" ]; then
  echo "$TESTEMAIL_RESPONSE - Aborting"
  exit
fi

echo "Test email sent successfully"

echo "Google reCAPTCHA - set up reCAPTCHA for your domain at https://www.google.com/recaptcha/"

readinput -e -p "Enter Google reCAPTCHA SITE key" -i "" google_recaptcha_site_key
readinput -e -p "Enter Google reCAPTCHA SECRET key" -i "" google_recaptcha_secret_key

echo "Elsevier API setup"

readinput -e -p "Elsevier API Key" -i "" elsevier_apikey
readinput -e -p "Elsevier Institution Token" -i "" elsevier_insttoken

echo "Database setup"

# MySQL database creation script from 
# https://raw.githubusercontent.com/saadismail/useful-bash-scripts/master/db.sh

# Use utf8mb4 to support full character set range
charset=utf8mb4

readinput -e -p "Name of new MySQL database to be used for X-Risk system" -i "xrisk" mysql_dbname
readinput -e -p "Name of new MySQL database user to be used in application" -i "xriskuser" mysql_username
read -p "Password for new MySQL database user (Note: password will be hidden): " -s mysql_password; echo
readinput -e -p "Path for MySQL backups (remove trailing slash)" -i "" mysql_backupdir

# If /root/.my.cnf doesn't exist then ask for root password
if ! [ -f /root/.my.cnf ]; then

	read -p "Root user MySQL password (Note: password will be hidden): " -s rootpasswd; echo

    export MYSQL_PWD=$rootpasswd
fi

DBEXISTS_VARIABLE=`mysqlshow --user=root ${mysql_dbname}| grep -v Wildcard | grep -o ${mysql_dbname}`
if [ "$DBEXISTS_VARIABLE" == ${mysql_dbname} ]; then
	echo "Database ${mysql_dbname} already exists, so aborting - need to start with clean database. To delete existing database, use 'DROP DATABASE dbname;'"
	exit
fi

echo "Creating new MySQL database..."
mysql -uroot -e "CREATE DATABASE ${mysql_dbname} CHARACTER SET ${charset};"

echo "Database successfully created"

USEREXISTS_VARIABLE="$(mysql -u root -sse "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = '$mysql_username')")"

if [ "$USEREXISTS_VARIABLE" = 1 ]; then
	mysql -uroot -e "DROP DATABASE ${mysql_dbname};"
	echo "User ${mysql_username} already exists, so aborting - need to start with new user. To delete existing user use 'DROP USER username@localhost;'"
	exit
fi

echo "Creating new user..."
mysql -uroot -e "CREATE USER '${mysql_username}'@'localhost' IDENTIFIED WITH mysql_native_password BY '${mysql_password}';"

echo "User successfully created"
echo "Granting all privileges on ${mysql_dbname} to ${mysql_username}"
mysql -uroot -e "GRANT ALL PRIVILEGES ON ${mysql_dbname}.* TO '${mysql_username}'@'localhost';"
mysql -uroot -e "FLUSH PRIVILEGES;"

echo "Database set up"
	
echo "
DOMAIN='${domain}' 
GOOGLE_RECAPTCHA_SITE_KEY='${google_recaptcha_site_key}'
GOOGLE_RECAPTCHA_SECRET_KEY='${google_recaptcha_secret_key}'
SECURE_SSL_REDIRECT=False
DEBUG=True
DB_ENGINE='django.db.backends.mysql'
DB_NAME='${mysql_dbname}'
DB_USER='${mysql_username}'
DB_PASSWORD='${mysql_password}'
DB_HOST='127.0.0.1'
DB_BACKUPDIR='${mysql_backupdir}'
EMAIL_HOST='${email_host}'
EMAIL_PORT=${email_port}
EMAIL_HOST_USER='${email_username}'
EMAIL_HOST_PASSWORD='${email_password}'
DEFAULT_FROM_EMAIL='${email_default_from}'
" > config.py

echo "
{
    \"apikey\": \"${elsevier_apikey}\",
    \"insttoken\": \"${elsevier_insttoken}\"
}
" > config.json

echo "Adding SECRET_KEY to config.py"
python3 addsecretkey.py

pip install -r requirements.txt
python3 manage.py makemigrations
python3 manage.py migrate

echo "Loading CMS data, enter MySQL root password: "
python3 manage.py loaddata cmsdata.json

echo "Creating superuser: "
python3 manage.py createsuperuser





