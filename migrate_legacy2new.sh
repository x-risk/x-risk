##########################
##########################
# Script to incorporate legacy x-risk database into new x-risk system, which may contain additional fields, applications, etc
# Run from new x-risk folder, eg. 'cd x-risk'
##########################
##########################

##########################
##########################
####### FUNCTIONS ########
##########################
##########################

##########################
# Function for querying user for data
##########################

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

##########################
# Load variables from Django config file
##########################

. config.py


##########################
# If /root/.my.cnf doesn't exist then ask for MySQL root password
##########################

if ! [ -f /root/.my.cnf ]; then

	read -p "Root user MySQL password (Note: password will be hidden): " -s rootpasswd; echo

    export MYSQL_PWD=$rootpasswd
fi


##########################
# It is assumed legacy data as SQL has been dumped and uploaded to xrisk_legacy.sql in parent directory, ie. ../xrisk_legacy.sql
# If not, query user to see if they want to dump out from an existing database on same server
# If legacy data/database not on same server, upload legacy data as SQL to this machine as '../xrisk_legacy.sql' prior to running this script
##########################

if ! [ -f ../xrisk_legacy.sql ]; then

    readinput -e -p "Name of legacy x-risk MySQL database to obtain legacy data from" -i "xrisk" mysql_legacy_dbname

    mysqldump -uroot $mysql_legacy_dbname > ../xrisk_legacy.sql
fi


###########################
# Clear database and user
###########################

mysql -uroot -e "DROP USER '${DB_USER}'@'localhost';"
mysql -uroot -e "DROP DATABASE ${DB_NAME};"


###########################
# Recreate database and user
###########################

mysql -uroot -e "CREATE DATABASE ${DB_NAME} CHARACTER SET utf8mb4;"
mysql -uroot -e "CREATE USER '${DB_USER}'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';"
mysql -uroot -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -uroot -e "FLUSH PRIVILEGES;"


###########################
# Get original source code for purposes of obtaining original migrations files
###########################
echo "Enter server root password:"
sudo rm -r ../x-risk_legacy
mkdir ../x-risk_legacy
git clone https://github.com/gormshackelford/x-risk.git ../x-risk_legacy


###########################
# Remove existing migrations in new source code
# NOTE: We are searching specific folders as general search will remove migrations from 'env' virtualenv folder
###########################
find . -path "*/engine/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/contentmanager/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/engine/migrations/*.pyc" -delete
find . -path "*/contentmanager/migrations/*.pyc" -delete


###########################
# Copy legacy migrations folder to ensure Django holds legacy state
###########################
cp -R ../x-risk_legacy/engine/migrations engine/


###########################
# Load legacy data into MySQL
###########################
echo "Loading legacy data into MySQL"
mysql -uroot ${DB_NAME} < ../xrisk_legacy.sql


###########################
# With database and migrations folder reverted to legacy state 
# we run 'makemigrations' to incorporate model changes
###########################
python3 manage.py makemigrations
python3 manage.py migrate


###########################
# Finally load CMS data and create superuser for CMS
###########################
python3 manage.py loaddata cmsdata.json
echo "Creating superuser"
python3 manage.py createsuperuser


