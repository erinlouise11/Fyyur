import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode. --- DONE 
DEBUG = True
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Connect to the database
# TODO IMPLEMENT DATABASE URL --- DONE
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Psqlpass!@localhost:5432/fyyursecond'
