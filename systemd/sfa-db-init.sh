#!/bin/bash

set -e

####################
PGDATA=/var/lib/pgsql/data/
PGLOG=/var/log/pgsql

postgresql_conf=$PGDATA/postgresql.conf
pg_hba_conf=$PGDATA/pg_hba.conf

# SFA consolidated (merged) config file
sfa_whole_config=/etc/sfa/sfa_config
# SFA default config (read-only template)
sfa_default_config=/etc/sfa/default_config.xml
# SFA local (site-dependent) file
sfa_local_config=/etc/sfa/configs/site_config
sfa_local_config_xml=/etc/sfa/configs/site_config.xml
sfa_local_config_sh=/etc/sfa/sfa_config.sh

# Regenerate configuration files - almost verbatim from plc.init
function reconfigure () {

    # Regenerate the main configuration file from default values
    # overlaid with site-specific and current values.
    files=( $sfa_default_config $sfa_local_config )
    tmp=$(mktemp /tmp/sfa_config.XXXXXX)
    sfa-config --python "${files[@]}" > $tmp
    if [ $? -eq 0 ] ; then
		mv $tmp $sfa_whole_config
		chmod 444 $sfa_whole_config
    else
		echo "SFA: Warning: Invalid configuration file(s) detected"
	    rm -f $tmp
        exit 1
    fi

    # Convert configuration to various formats
    if [ -f $sfa_local_config_xml ] ; then
        sfa-config --python $sfa_local_config_xml > $sfa_local_config
        rm $sfa_local_config_xml
    fi
    if [ -n "$force" -o $sfa_local_config -nt $sfa_whole_config ] ; then
    	sfa-config --python $sfa_default_config $sfa_local_config > $sfa_whole_config
    fi
    if [ -n "$force" -o $sfa_whole_config -nt /etc/sfa/sfa_config.sh ] ; then
    	sfa-config --shell $sfa_default_config $sfa_local_config > /etc/sfa/sfa_config.sh
    fi

    # reload the shell version
    source $sfa_local_config_sh

}

function postgresql_setting() {
    param="$1"; shift
    value="$1"; shift

    sed --regexp-extended --in-place \
      --expression="s|#?${param} = .*|${param} = ${value}|" \
      $postgresql_conf
}

function start () {

    # only if enabled
    [ "$SFA_DB_ENABLED" == 1 -o "$SFA_DB_ENABLED" == True ] || return

    postgresql_setting port "'$SFA_DB_PORT'"
    mkdir -p $PGLOG
    chown postgres:postgres $PGLOG
    postgresql_setting log_directory "'$PGLOG'"

    ######## /var/lib/pgsql/data
    # Fix ownership (rpm installation may have changed it)
    chown -R -H postgres:postgres $(dirname $PGDATA)

    # PostgreSQL must be started at least once to bootstrap
    # /var/lib/pgsql/data
    if [ ! -f $postgresql_conf ] ; then
        /usr/bin/postgresql-setup --initdb --unit postgresql
    fi

    ######## /var/lib/pgsql/data/postgresql.conf
    registry_ip=""
    foo=$(python -c "import socket; print socket.gethostbyname('$SFA_REGISTRY_HOST')") && registry_ip="$foo"
    # Enable DB server. drop Postgresql<=7.x
    # PostgreSQL >=8.0 defines listen_addresses
    # listen on a specific IP + localhost, more robust when run within a vserver
    sed -i -e '/^listen_addresses/d' $postgresql_conf
    if [ -z "$registry_ip" ] ; then
        postgresql_setting listen_addresses "'localhost'"
    else
        postgresql_setting listen_addresses "'${registry_ip},localhost'"
    fi
    postgresql_setting timezone "'UTC'"
    postgresql_setting log_timezone "'UTC'"

    ######## /var/lib/pgsql/data/pg_hba.conf
    # remove/recreate passwordless localhost entry
    sed -i -e "/^local/d" $pg_hba_conf
    echo "local all all trust" >> $pg_hba_conf

    # Disable access to our DB from all hosts
    sed -i -e "/^host ${SFA_DB_NAME}/d" $pg_hba_conf
    # grant access
    {
        echo "host $SFA_DB_NAME $SFA_DB_USER 127.0.0.1/32 password"
        [ -n "$registry_ip" ] && echo "host $SFA_DB_NAME $SFA_DB_USER ${registry_ip}/32 password"
    } >> $pg_hba_conf

    # Fix ownership (sed -i changes it)
    chown postgres:postgres $postgresql_conf $pg_hba_conf

    ######## compute a password if needed
    if [ -z "$SFA_DB_PASSWORD" ] ; then
        SFA_DB_PASSWORD=$(uuidgen)
        sfa-config --category=sfa_db --variable=password --value="$SFA_DB_PASSWORD" --save=$sfa_local_config $sfa_local_config >& /dev/null
        reconfigure
    fi

    systemctl restart postgresql

    ######## make sure we have the user and db created
    # user
    if ! psql -U $SFA_DB_USER -c "" template1 >/dev/null 2>&1 ; then
    	psql -U postgres -c "CREATE USER $SFA_DB_USER PASSWORD '$SFA_DB_PASSWORD'" template1 >& /dev/null
    else
        psql -U postgres -c "ALTER USER $SFA_DB_USER WITH PASSWORD '$SFA_DB_PASSWORD'" template1 >& /dev/null
    fi

    # db
    if ! psql -U $SFA_DB_USER -c "" $SFA_DB_NAME >/dev/null 2>&1 ; then
    	createdb -U postgres --template=template0 --encoding=UNICODE --owner=$SFA_DB_USER $SFA_DB_NAME
    fi

    # create schema; sfaadmin.py is safer than just sfaadmin
    sfaadmin.py reg sync_db

}

# source shell config if present
# but it might not be present the very first time
[ ! -f $sfa_local_config_sh ] && reconfigure

source $sfa_local_config_sh

# Export so that we do not have to specify -p to psql invocations
export PGPORT=$SFA_DB_PORT

start
