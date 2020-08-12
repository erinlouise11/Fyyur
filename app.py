#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

# importing migrate functionality
from flask_migrate import Migrate

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

# connecting to the database provided in the config file along with the track modifications setting
app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

# Genre table to hold all the genre types
# this will be linking a m-m relationship to artists and venues using the artist and venue association tables 
class Genre(db.Model):

  __tablename__ = 'Genre'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String)

# association table to link the artists to their genres
artist_genres = db.Table('artist_genres',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True)
)

# association table to link the venues to their genres
venue_genres = db.Table('venue_genres',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
)

class Venue(db.Model):

  __tablename__ = 'Venue'

  id = db.Column(db.Integer, primary_key=True)
  # adding the foreign key to the details table 
  details_id = db.Column(db.Integer, db.ForeignKey('Details.id'), nullable=False)
  name = db.Column(db.String)
  seeking_talent = db.Column(db.Boolean, default=False, nullable=False)
  seeking_text = db.Column(db.String)  
  # creating a relationship to the show table 
  shows = db.relationship('Show', backref='venue', lazy=True)
  # linking the m-m relationship with the venue secondary association table 
  genres = db.relationship('Genre', secondary=venue_genres, backref=db.backref('venues'))

  # print out formatting
  def __repr__(self):
    return f'<Venue {self.id} {self.name} {self.seeking_talent}>'

class Artist(db.Model):

  __tablename__ = 'Artist'

  id = db.Column(db.Integer, primary_key=True)
  # adding the foreign key for the details table 
  details_id = db.Column(db.Integer, db.ForeignKey('Details.id'), nullable=False)
  name = db.Column(db.String)
  seeking_venue = db.Column(db.Boolean, default=False, nullable=False)
  seeking_text = db.Column(db.String)
  # creating a relationship to the show table 
  shows = db.relationship('Show', backref='artist', lazy=True)
  # linking the m-m relationship with the artist secondary association table 
  genres = db.relationship('Genre', secondary=artist_genres, backref=db.backref('artists'))

  # print out formatting
  def __repr__(self):
    return f'<Artist {self.id} {self.name} {self.seeking_venue}>'

# details table to hold the information about a venue or artist to avoid redundancy
# including address, contact and links
class Details(db.Model):

  __tablename__ = "Details"

  id = db.Column(db.Integer, primary_key=True)
  city = db.Column(db.String(120))
  state = db.Column(db.String(120))
  address = db.Column(db.String)
  phone = db.Column(db.String(120))
  website = db.Column(db.String)
  image_link = db.Column(db.String(500))
  facebook_link = db.Column(db.String(120))
  # creating the relationships between the artist and venue tables
  venue_details = db.relationship('Venue', backref='details', lazy=True)
  artist_details = db.relationship('Artist', backref='details', lazy=True)

  # print out formatting
  def __repr__(self):
    return f'<Detail {self.id} Info {self.city} {self.state} {self.phone} {self.website} {self.image_link} {self.facebook_link}>'

# show table to hold upcoming and past shows for both artists and venues
# including a boolean to tell whether it's upcoming or past and the start time
class Show(db.Model):

  __tablename__ = "Show"
  
  id = db.Column(db.Integer, primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
  upcoming = db.Column(db.Boolean, nullable=False)
  start_time = db.Column(db.DateTime)

  # print out formatting
  def __repr__(self):
    return f'<Show {self.id} {self.start_time} artist_id={artist_id} venue_id={venue_id}>'

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  # getting all the venue information from the table and creating containers
  venues = Venue.query.all()
  venueData = [] 
  statesAndCities = set()

  # get the corresponding detail from the Details table for each venue
  # add them as a tuple to the set
  for venue in venues:    
    detail = Details.query.filter_by(id=venue.details_id).one()
    statesAndCities.add((detail.city, detail.state))

  # creating a list from the set
  statesAndCities = list(statesAndCities)

  # adding the places to a dictionary and checking for venues at the place given by 'place'
  for place in statesAndCities:
    listOfVenues = []

    for venue in venues:
      detail = Details.query.filter_by(id=venue.details_id).one()

      if (detail.city == place[0]) and (detail.state == place[1]):
        
        # adding all the venue details to the venue dictionary 
        listOfVenues.append({
          "id": venue.id, 
          "name": venue.name 
        })

    # adding all the cities, states and venues to the data dictionary
    venueData.append({
      "city": place[0], 
      "state": place[1], 
      "venues": listOfVenues
    })  

  return render_template('pages/venues.html', areas=venueData)

@app.route('/venues/search', methods=['POST'])
def search_venues():

  # get the search term from the form
  # and create a filter variable to use in the filter method (both case insensitive and any string containing the search term)
  # apply filter to obtain all possible values
  venueData = []
  search = request.form.get('search_term', '').strip()  
  filterTerm = Venue.name.ilike('%'+search+'%')    
  venues = Venue.query.filter(filterTerm).all() 
  count = len(venues) # amount of results

  # traverse the results and get the display data 
  # id used for future navigation (not diaplyed) and name for diaplaying the venue name  
  for venue in venues:
    venueData.append({
      "id": venue.id, 
      "name": venue.name
    })

  # putting the amount of results as well as the name data in a response   
  response = {
    "count": count, 
    "data": venueData
  }

  return render_template('pages/search_venues.html', results=response, search_term=search)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  
  # get the venue at the given id
  venue = Venue.query.filter_by(id=venue_id).one_or_none()  

  # if the venue exists
  if (venue):    
    # create a detail variable to hold all the venue information
    # create lists to hold the genres, upcoming shows, past shows and their counts
    detail = Details.query.filter_by(id=venue.details_id).one()       
    
    showsUpcoming = []
    showsPast = []
    genresList = []
    numUpcoming = 0    
    numPast = 0        

    # using the shows in the venues table, get the respective artist data and artist details  
    for show in venue.shows:
      artist = Artist.query.filter_by(id=show.artist_id).one()
      artistDetail = Details.query.filter_by(id=artist.details_id).one()
      startTime = str(show.start_time)
      
      # using the upcoming column in the show table to say whether upcoming or past and count how many of each (true is upcoming, false is past)
      # if its upcoming or past, append the relevant artist data (image, id for navigation, artist name and datetime converted to string)
      if (show.upcoming):
        numUpcoming += 1
        
        showsUpcoming.append({
          'artist_image_link': artistDetail.image_link,
          'artist_id': artist.id, 
          'artist_name': artist.name,           
          'start_time': startTime
        })

      else:
        numPast += 1

        showsPast.append({
          'artist_image_link': artistDetail.image_link,
          'artist_id': artist.id, 
          'artist_name': artist.name,           
          'start_time': startTime
        })
        
    # traversing the genres in the given venue and adding them to a list
    for genre in venue.genres:
      genresList.append(genre.name)

    # putting all the data together for returning
    venueData = {
            'id': venue_id,
            'name': venue.name,
            'genres': genresList,  
            'state': detail.state,          
            'city': detail.city,            
            'address': detail.address,
            'phone': detail.phone,
            'website': detail.website,
            'facebook_link': detail.facebook_link,
            'seeking_talent': venue.seeking_talent,
            'seeking_description': venue.seeking_text,            
            'past_shows': showsPast,
            'past_shows_count': numPast,
            'upcoming_shows': showsUpcoming,
            'upcoming_shows_count': numUpcoming,    
            'image_link': detail.image_link        
        }

    return render_template('pages/show_venue.html', venue=venueData)

  # if the venue does not exist, print error message and display null values
  else:
    errorMessage = 'ID Error: Not Found!'
    nullMessage = ''

    venueData = {
            'id': errorMessage,
            'name': nullMessage,
            'genres': nullMessage,  
            'state': nullMessage,          
            'city': nullMessage,            
            'address': nullMessage,
            'phone': nullMessage,
            'website': nullMessage,
            'facebook_link': nullMessage,
            'seeking_talent': nullMessage,
            'seeking_description': nullMessage,            
            'past_shows': nullMessage,
            'past_shows_count': nullMessage,
            'upcoming_shows': nullMessage,
            'upcoming_shows_count': nullMessage,    
            'image_link': nullMessage        
        }

    return render_template('pages/show_venue.html', venue=venueData)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  # getting the data from the form
  # only using fields that are referenced in new_venue.html
  form = VenueForm()  
  genres = form.genres.data
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data.strip()
  address = form.address.data.strip()
  phone = form.phone.data.strip() 
  facebook_link = form.facebook_link.data.strip()  
  createError = False

  # use the form details to add a record into the Details table & commit the changes
  # use the newly made details_id (use facebook_link to find unique) in the Venue table to create the new venue item 
  try:
    newDetail = Details(city=city, state=state, address=address, phone=phone, facebook_link=facebook_link)
    db.session.add(newDetail)
    db.session.commit()

    detail = Details.query.filter_by(facebook_link=newDetail.facebook_link).one()
    newVenue = Venue(name=name, details_id=detail.id)

    # find the genre object to add from the Genre db
    # and append it to the newVenue genres
    for genre in genres: 
      newVenue.genres.append(Genre.query.filter_by(name=genre).one())     

    # adding the newVenue record to the Venue table
    db.session.add(newVenue)
    db.session.commit()
  except: 
    createError = True   
    db.session.rollback()
  finally:
    db.session.close() 

  # if there was a createError during try/catch, 
  # then flash error message and redirect to the create page to try again
  # else flash success message and go back to the home page
  if (createError):
    flash('An error occurred. Venue ' + name + ' could not be listed.')
    return redirect(url_for('create_venue_submission'))    
  else:
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # get the venue item using the venue_id given
  venue = Venue.query.filter_by(id=venue_id).one()  
  deleteError = False

  # delete the mtching venue item from the session/database
  try:    
    db.session.delete(venue)
    db.session.commit()
  except:
    deleteError = True
    db.session.rollback()
  finally:
    db.session.close()

  # if there was a deleteError during the try catch, then abort
  # else return a successful json message 
  if (deleteError):
    abort(500)
  else:
    return jsonify({
      "deleted": True,
    })

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  # get all the artists in the artist table 
  artistData = []
  artists = Artist.query.all()  

  # traverse the artists and append them to the artistData
  # id used for future navigation (not displyed) and name for displaying the venue name 
  for artist in artists:
    artistData.append({
      'id': artist.id,
      'name': artist.name
    })

  return render_template('pages/artists.html', artists=artistData)

@app.route('/artists/search', methods=['POST'])
def search_artists():

  # get the search term from the form
  # and create a filter variable to use in the filter method (both case insensitive and any string containing the search term)
  # apply filter to obtain all possible values 
  artistData = []
  search = request.form.get('search_term', '').strip()
  filterTerm = Artist.name.ilike('%'+search+'%')
  artists = Artist.query.filter(filterTerm).all() 
  count = len(artists) # amount of results 

  # traverse the results and get the display data 
  # id used for future navigation (not diaplyed) and name for diaplaying the venue name 
  for artist in artists:
    artistData.append({
      'id': artist.id,
      'name': artist.name
    })

  # putting the amount of results as well as the name data in a response  
  response = {
    'count': count, 
    'data': artistData
  }

  return render_template('pages/search_artists.html', results=response, search_term=search)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id

  # get the venue at the given id
  artist = Artist.query.filter_by(id=artist_id).one_or_none()

  # if the artist exists 
  if (artist):
    # get the detail item and the genres for the artist_id
    detail = Details.query.filter_by(id=artist.details_id).one()   
    
    showsUpcoming = []
    showsPast = []
    genresList = []
    numUpcoming = 0    
    numPast = 0   

    # using the shows in the artist table, get the respective venue data and venue details
    for show in artist.shows:
      venue = Venue.query.filter_by(id=show.venue_id).one()
      venueDetails = Details.query.filter_by(id=venue.details_id).one()
      startTime = str(show.start_time)

      # using the upcoming column in the show table to determine whether upcoming or past and count how many of each (true is upcoming, false is past)
      # if its upcoming or past, append the relevant artist data (image, id for navigation, artist name and datetime converted to string)
      if (show.upcoming):
        numUpcoming += 1

        showsUpcoming.append({
          'venue_image_link': venueDetails.image_link,
          'venue_id': show.venue_id, 
          'venue_name': show.venue.name,           
          'start_time': startTime
        })

      else:
        numPast += 1

        showsPast.append({
          'venue_image_link': venueDetails.image_link,
          'venue_id': show.venue_id, 
          'venue_name': show.venue.name,           
          'start_time': startTime
        })

    # traversing the genres in the given venue and adding them to a list
    for genre in artist.genres:
      genresList.append(genre.name)

    # putting all the data together for returning
    artistData = {
            'id': artist_id,
            'name': artist.name,
            'genres': genresList,  
            'state': detail.state,          
            'city': detail.city,   
            'phone': detail.phone,
            'website': detail.website,
            'facebook_link': detail.facebook_link,
            'seeking_venue': artist.seeking_venue,
            'seeking_description': artist.seeking_text,            
            'past_shows': showsPast,
            'past_shows_count': numPast,
            'upcoming_shows': showsUpcoming,
            'upcoming_shows_count': numUpcoming,    
            'image_link': detail.image_link            
        }
    return render_template('pages/show_artist.html', artist=artistData)

  # if the artist does not exist, print error message and display null values
  else:
    errorMessage = 'ID Error: Not Found!'
    nullMessage = ''

    artistData = {
            'id': errorMessage,
            'name': nullMessage,
            'genres': nullMessage,  
            'state': nullMessage,          
            'city': nullMessage,
            'phone': nullMessage,
            'website': nullMessage,
            'facebook_link': nullMessage,
            'seeking_venue': nullMessage,
            'seeking_description': nullMessage,            
            'past_shows': nullMessage,
            'past_shows_count': nullMessage,
            'upcoming_shows': nullMessage,
            'upcoming_shows_count': nullMessage,    
            'image_link': nullMessage
        }
    return render_template('pages/show_artist.html', artist=artistData)
  
#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):

  # basing the form values accoring to the detail table as this is where all the information is
  # the name of the artist is still in the artist table, so I have added that into the form using the artist.id
  # It is as a placeholder for now as I am unsure how to make it work without changing my whole db setup
  # would you be able to help me with this?

  # get the artist at the given id 
  artist = Artist.query.filter_by(id=artist_id).one_or_none()  

  # if the artist exists
  if (artist):

    # get the respective detial from the details table 
    # setting the form to use the detail object
    detail = Details.query.filter_by(id=artist.details_id).one()
    artistForm = ArtistForm(obj=detail)
    genresList = []

    # traversing the genres of the given artist and adding them to the list to be used in the form 
    for genre in artist.genres:
      genresList.append(genre.name)    

    artistData = {
            'id': artist_id,
            'name': artist.name,
            'genres': genresList,  
            'state': detail.state,          
            'city': detail.city,   
            'phone': detail.phone,
            'website': detail.website,
            'facebook_link': detail.facebook_link,
            'seeking_venue': artist.seeking_venue,
            'seeking_description': artist.seeking_text,    
            'image_link': detail.image_link      
          }   

    return render_template('forms/edit_artist.html', form=artistForm, artist=artistData)
  
  # if the artist does not exist, because its using a form, I cannot send null values
  # instead, I am just aborting the request
  else:
    abort(500)   

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # artist record with ID <artist_id> using the new attributes

  # getting the data from the form 
  form = ArtistForm()  
  genres = form.genres.data
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data.strip()
  phone = form.phone.data
  facebook_link = form.facebook_link.data.strip()

  # get the respective artist and detail items to be used in the record update
  artist = Artist.query.filter_by(id=artist_id).one_or_none()
  detail = Details.query.filter_by(id=artist.details_id).one()  
  updateError = False

  # resending all the data to the db and redirecting to the artist page
  # I am only including the fields that are currently in the edit_artist.html form
  try:
    artist.name = name   
    detail.city = city
    detail.state = state
    detail.phone = phone
    detail.facebook_link = facebook_link

    # clear the genres so we can add them as new ones
    # find the genre object to add from the Genre db
    # and append it to the artist genres
    artist.genres.clear()
    for genre in genres: 
      artist.genres.append(Genre.query.filter_by(name=genre).one())
    
    db.session.commit()    
  except: 
    updateError = True
    db.session.rollback()
  finally:
    db.session.close()   

  # if throughout the try catch, there was an updateError, then abort 
  # else redirect accordingly
  if(updateError):
    abort(500)
  else:
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):

  # basing the form values accoring to the detail table as this is where all the information is
  # the name of the venue is still in the venue table, so I have added that into the form using the venue.id
  # It is as a placeholder for now as I am unsure how to make it work without changing my whole db setup
  # would you be able to help me with this?

  # get the venue at the given id 
  venue = Venue.query.filter_by(id=venue_id).one_or_none()  

  # if the venue exists
  if (venue):

    # get the respective detial from the details table 
    # setting the form to use the detail object 
    detail = Details.query.filter_by(id=venue.details_id).one()
    form = VenueForm(obj=detail)
    genresList = []    

    # traversing the genres in the given venue and adding them to a list
    for genre in venue.genres:
      genresList.append(genre.name)

    venueData = {
              'id': venue_id,
              'name': venue.name,
              'genres': genresList,  
              'state': detail.state,          
              'city': detail.city,            
              'address': detail.address,
              'phone': detail.phone,
              'website': detail.website,
              'facebook_link': detail.facebook_link,
              'seeking_talent': venue.seeking_talent,
              'seeking_description': venue.seeking_text,    
              'image_link': detail.image_link      
            }   
    
    return render_template('forms/edit_venue.html', form=form, venue=venueData)
  
  # if the venue does not exist, then abort 
  else:
    abort(500)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # venue record with ID <venue_id> using the new attributes

  # getting the dat from the form
  form = VenueForm()  
  genres = form.genres.data
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data.strip()
  phone = form.phone.data.strip()
  facebook_link = form.facebook_link.data.strip()

  # get the respective venue and detail items to be used in the record update
  venue = Venue.query.filter_by(id=venue_id).one_or_none()
  detail = Details.query.filter_by(id=venue.details_id).one()  
  updateError = False

  # resending all the data to the db and redirecting to the venue page
  try: 
    venue.name = name   
    detail.city = city
    detail.state = state
    detail.phone = phone
    detail.facebook_link = facebook_link

    # clear the current genres in order to use the new ones
    # find the genre object to add from the Genre db
    # and append it to the artist genres
    venue.genres.clear()
    for genre in genres: 
      venue.genres.append(Genre.query.filter_by(name=genre).one())
    
    db.session.commit()
  except: 
    updateError = True 
    db.session.rollback()
  finally:
    db.session.close()   

  # if throughout the try catch, there was an updateError, then abort 
  # else redirect accordingly
  if(updateError):
    abort(500)
  else:
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form

  # get the form data from the ArtistForm() method
  # only using fields that are referenced in new_artist.html
  form = ArtistForm()  
  genres = form.genres.data
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data.strip()
  phone = form.phone.data.strip() 
  facebook_link = form.facebook_link.data.strip()  
  updateError = False

  # use the form details to add a record into the Details table & commit the changes
  # use the newly made details_id (use facebook_link to find unique) in the Artist table to create the new artist item 
  try:    
    newDetail = Details(city=city, state=state, phone=phone, facebook_link=facebook_link)
    db.session.add(newDetail)
    db.session.commit()

    detail = Details.query.filter_by(facebook_link=newDetail.facebook_link).one()
    newArtist = Artist(name=name, details_id=detail.id)

    # find the genre object to add from the Genre db
    # and append it to the newArtist genres
    for genre in genres: 
      newArtist.genres.append(Genre.query.filter_by(name=genre).one()) 

    # add the new record to the Artist table and commit the changes
    db.session.add(newArtist)
    db.session.commit()
  except:
    updateError = True
    db.session.rollback()
  finally:
    db.session.close() 

  # if throughout the try catch, there was an updateError
  # then flash the error message and navigate back to the create show page to start again
  # else flash the successful message and navigate to the home page
  if(updateError):
    flash('An error occurred. Artist ' + name + ' could not be listed.')
    return redirect(url_for('create_artist_submission'))
  else:
    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html') 

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows

  # get all the data from the shows table 
  showData = []
  shows = Show.query.all()  

  # getting the show data from the respective tables 
  for show in shows:
    artist = Artist.query.filter_by(id=show.artist_id).one()
    venue = Venue.query.filter_by(id=show.venue_id).one()
    detail = Details.query.filter_by(id=artist.details_id).one()
    startTime = str(show.start_time)

    # converting datetime to string and appending all the show data
    showData.append({
      'artist_image_link': detail.image_link, 
      'start_time': startTime,
      'artist_id': show.artist_id, 
      'artist_name': artist.name,
      'venue_id': show.venue_id, 
      'venue_name': venue.name  
    })
  
  return render_template('pages/shows.html', shows=showData)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form

  # get the form data from the ShowForm() method
  form = ShowForm()
  venueId = form.venue_id.data.strip()
  artistId = form.artist_id.data.strip()  
  startTime = form.start_time.data
  updateError = False

  # check if the show is upcoming or not to determine the value for the 'upcoming' column in the show table
  time = datetime.now()
  if(startTime > time):
    upcomingShow = True
  else:
    upcomingShow = False 

  # use the new show details from the form and our upcoming variable to create a new entry in the Show table
  try:    
    newShow = Show(artist_id=artistId, venue_id=venueId, start_time=startTime, upcoming=upcomingShow)
    db.session.add(newShow)
    db.session.commit()
  except:
    updateError = True
    db.session.rollback()
  finally:
    db.session.close() 

  # if throughout the try catch, there was an updateError
  # then flash the error message and navigate back to the create show page to start again
  # else flash the successful message and navigate to the home page
  if (updateError):
    flash('An error occurred. Show could not be listed.')
    return redirect(url_for('create_show_submission'))
  else:
    # on successful db insert, flash success
    flash('Show was successfully listed!')
    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
