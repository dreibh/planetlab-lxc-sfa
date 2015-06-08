# this move is about adding a 'name' column in the 'authority' table

#from sfa.util.sfalogging import logger

from sqlalchemy import MetaData, Table, Column, String
from migrate.changeset.schema import create_column, drop_column

def upgrade(migrate_engine):
    metadata = MetaData(bind = migrate_engine)
    authorities = Table('authorities', metadata, autoload=True)
    name_column = Column('name', String)
    name_column.create(authorities)

def downgrade(migrate_engine):
    metadata = MetaData(bind = migrate_engine)
    authorities = Table('authorities', metadata, autoload=True)
    authorities.c.name.drop()
