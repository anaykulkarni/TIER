import os
import re
from datetime import time, datetime, timedelta
import pandas as pd
from tier.environment.api_base import API_base
from rapidfuzz import fuzz

class EnglishDictionaryAPI(API_base):
    def execute(self, **params):
        """
        Get the definition and example sentence for a word.
        
        Required params:
        - word: str - The word to look up
        
        Returns:
        - Dictionary with word data or error information
        """
        expected_params = {"word"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        word = params.get("word")
        
        is_valid, error = self.validate_type(word, "word", str)
        if not is_valid:
            return error
        
        result = self.df[self.df['word'] == word]

        if result.empty:
            return {
                "status_code": 404,
                "error": "Word not found",
            }

        return {
            "status_code": 200,
            "word": word,
            "definition": result["definition"].item(),
            "example_sentence": result["example sentence"].item()
        }
        
class SpanishDictionaryAPI(API_base):
    def execute(self, **params):
        """
        Get the definition and example sentence for a word.
        
        Required params:
        - word: str - The word to look up
        
        Returns:
        - Dictionary with word data or error information
        """
        expected_params = {"word"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        word = params.get("word")
        
        is_valid, error = self.validate_type(word, "word", str)
        if not is_valid:
            return error
        
        result = self.df[self.df['word'] == word]
        if result.empty:
            return {
                "status_code": 404,
                "error": "Word not found",
            }
        
        return {
            "status_code": 200,
            "word": word,
            "definition": result["definition"].item(),
            "example_sentence": result["example sentence"].item()
        }

class CryptoPriceAPI(API_base):

    def execute(self, **params):
        """
        Get the price of a specific crypto currency
        
        Required params:
        - ticker: str - The ticker symbol of the crypto currency
        - price_time: str - This is a string in YYYY-MM-DD format
        
        Returns:
        - Dictionary with price information
        """
        expected_params = {"ticker", "price_time"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        ticker = params.get("ticker")
        price_time = params.get("price_time")  # This is a string in YYYY-MM-DD format
        
        is_valid, error = self.validate_type(ticker, "ticker", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(price_time, "price_time", str)
        if not is_valid:
            return error
        
        # Validate date format
        try:
            # Convert string to datetime for comparison
            price_date = datetime.strptime(price_time, '%Y-%m-%d').date()
            current_date = datetime.now().date()
            # Check if date is in the future
            is_valid, error = self.validate_param(
                price_date <= current_date,
                "Price time cannot be in the future",
                error_code=400
            )
            if not is_valid:
                return error
        except ValueError:
            return self.handle_error("price_time must be in YYYY-MM-DD format", 400)

        
        result = self.df[self.df['ticker'] == ticker]
        if result.empty:
            return {
                "status_code": 404,
                "error": "Cryptocurrency not found",
            }
        
        date_filter = result[result['date'] == price_time]
        if date_filter.empty:
            return {
                "status_code": 404,
                "error": "Price data for given date not found",
            }
        
        price = date_filter['price'].item()

        return {
            "status_code": 200,
            "ticker": ticker,
            "price_time": price_time,
            "price": price,
        }
       
class StockPriceAPI(API_base):
    def execute(self, **params):
        """
        Get the last traded price of a specific stock on a given day
        
        Required params:
        - ticker: str - The ticker symbol of the stock
        - price_time: str - This is a string in YYYY-MM-DD format
        
        Returns:
        - Dictionary with price information
        """
        expected_params = {"ticker", "price_time"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        ticker = params.get("ticker")
        price_time = params.get("price_time")  # This is a string in YYYY-MM-DD format
        
        is_valid, error = self.validate_type(ticker, "ticker", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(price_time, "price_time", str)
        if not is_valid:
            return error
        
        # Validate date format
        try:
            # Convert string to datetime for comparison
            price_date = datetime.strptime(price_time, '%Y-%m-%d').date()
            current_date = datetime.now().date()
            # Check if date is in the future
            is_valid, error = self.validate_param(
                price_date <= current_date,
                "Price time cannot be in the future",
                error_code=400
            )
            if not is_valid:
                return error
        except ValueError:
            return self.handle_error("price_time must be in YYYY-MM-DD format", 400)

        
        result = self.df[self.df['ticker'] == ticker]
        if result.empty:
            return {
                "status_code": 404,
                "error": "Stock not found",
            }
        
        date_filter = result[result['date'] == price_time]
        if date_filter.empty:
            return {
                "status_code": 404,
                "error": "Price data for given date not found",
            }
        
        price = date_filter['price'].item()

        return {
            "status_code": 200,
            "ticker": ticker,
            "price_time": price_time,
            "price": price,
        }
        

class BookSearchAPI(API_base):
    def execute(self, **params):
        """
        Search for books by title and optionally by author.
        
        Required params:
        - book_name: str - Title of the book to search for
        
        Optional params:
        - author: str - Author name to filter by
        
        Returns:
        - Dictionary with found book(s) or error information
        """
        expected_params = {"book_name", "author"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        book_name = params.get("book_name")
        author = params.get("author")
        
        # Validate parameters
        is_valid, error = self.validate_type(book_name, "book_name", str)
        if not is_valid:
            return error
        
        if author is not None:
            is_valid, error = self.validate_type(author, "author", str)
            if not is_valid:
                return error
        
        # Filter by title (case-insensitive)
        title_mask = self.df['title'].str.lower() == book_name.lower()
        filtered_df = self.df[title_mask]
        
        if filtered_df.empty:
            return self.handle_error(f"No books found with title '{book_name}'", 404)
        
        # Filter by author if provided
        if author:
            author_mask = filtered_df['author'].str.lower() == author.lower()
            filtered_df = filtered_df[author_mask]
            
            if filtered_df.empty:
                # Check if author exists in the database
                author_exists = (self.df['author'].str.lower() == author.lower()).any()
                if author_exists:
                    return self.handle_error(
                        f"Author '{author}' exists in our database but didn't write '{book_name}'",
                        404
                    )
                else:
                    return self.handle_error(f"No books found by author '{author}'", 404)
        
        # Convert DataFrame to list of dictionaries
        books = filtered_df.to_dict('records')
        
        # Return results
        if len(books) == 1:
            # If only one book matches, return it directly with success flag
            result = books[0].copy()
            result["status_code"] = 200
            return result
        else:
            # If multiple books match, return them as a list with metadata
            return {
                "status_code": 200,
                "count": len(books),
                "message": f"Found {len(books)} books matching '{book_name}'" + 
                          (f" by '{author}'" if author else ""),
                "books": books
            }
                      
class MovieSearchAPI(API_base):
    def execute(self, **params):
        """
        Search for movies by title and optionally by director.
        
        Required params:
        - movie_title: str - Title of the movie to search for
        
        Optional params:
        - director: str - Director name to filter by
        
        Returns:
        - Dictionary with found movie(s) or error information
        """
        expected_params = {"movie_title", "director"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        movie_title = params.get("movie_title")
        director = params.get("director")
        
        # Validate parameters
        is_valid, error = self.validate_type(movie_title, "movie_title", str)
        if not is_valid:
            return error
        
        if director is not None:
            is_valid, error = self.validate_type(director, "director", str)
            if not is_valid:
                return error
        
        # Filter by title
        title_mask = self.df['title'].str.lower() == movie_title.lower()
        filtered_df = self.df[title_mask]
        
        if filtered_df.empty:
            return self.handle_error(f"No movies found with title '{movie_title}'", 404)
        
        # Filter by director if provided
        if director:
            director_mask = filtered_df['director'].str.lower() == director.lower()
            filtered_df = filtered_df[director_mask]
            
            if filtered_df.empty:
                # Check if director exists in the database
                director_exists = (self.df['director'].str.lower() == director.lower()).any()
                if director_exists:
                    return self.handle_error(
                        f"Director '{director}' exists in our database but didn't direct '{movie_title}'",
                        404
                    )
                else:
                    return self.handle_error(f"No movies found by director '{director}'", 404)
        
        # Convert DataFrame to list of dictionaries
        movies = filtered_df.to_dict('records')
        
        # Return results
        if len(movies) == 1:
            # If only one movie matches, return it directly with success flag
            result = movies[0].copy()
            result["status_code"] = 200
            return result
        else:
            # If multiple movies match, return them as a list with metadata
            return {
                "status_code": 200,
                "count": len(movies),
                "message": f"Found {len(movies)} movies matching '{movie_title}'" + 
                          (f" by '{director}'" if director else ""),
                "movies": movies
            }
            
class CurrencyExchangeAPI(API_base):
    
    def is_currency_supported(self, from_currency, to_currency):
        """
        Check if the currency pair is supported using pandas DataFrame operations.
        
        Args:
            from_currency (str): Source currency code
            to_currency (str): Target currency code
        
        Returns:
            bool: True if the currency pair is supported, False otherwise.
        """
        # Check if direct conversion exists
        direct_match = self.df[(self.df['from'] == from_currency) & (self.df['to'] == to_currency)]
        if not direct_match.empty:
            return True
        
        # Check if inverse conversion exists
        inverse_match = self.df[(self.df['from'] == to_currency) & (self.df['to'] == from_currency)]
        return not inverse_match.empty

    def get_exchange_rate(self, from_currency, to_currency):
        """
        Get the exchange rate for a currency pair using pandas DataFrame operations.
        
        Args:
            from_currency (str): Source currency code
            to_currency (str): Target currency code
        
        Returns:
            float: Exchange rate, or None if not found
        """
        # Try direct conversion first
        direct_match = self.df[(self.df['from'] == from_currency) & (self.df['to'] == to_currency)]
        if not direct_match.empty:
            return direct_match['rate'].iloc[0]
        
        # Try inverse conversion
        inverse_match = self.df[(self.df['from'] == to_currency) & (self.df['to'] == from_currency)]
        if not inverse_match.empty:
            return 1 / inverse_match['rate'].iloc[0]
        
        return None
    
    def execute(self, **params):
        """
        Execute currency conversion.
        
        Required params:
        - amount: float/int - Amount to convert
        - from_currency: str - Source currency code
        - to_currency: str - Target currency code
        
        Returns:
        - Dictionary with conversion results or error information
        """
        expected_params = {"amount", "from_currency", "to_currency"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        amount = params.get("amount")
        from_currency = params.get("from_currency")
        to_currency = params.get("to_currency")

        # Validate parameters
        is_valid, error = self.validate_type(amount, "amount", (float, int))
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(from_currency, "from_currency", str)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(to_currency, "to_currency", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_param(
            amount > 0,
            "Amount must be positive",
            400
        )
        if not is_valid:
            return error
        
        # Check if currency pair is supported
        if not self.is_currency_supported(from_currency, to_currency):
            return self.handle_error(f"Currency pair ({from_currency}, {to_currency}) not supported", 404)

        # Get exchange rate
        rate = self.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            return self.handle_error(f"Exchange rate not found for ({from_currency}, {to_currency})", 404)

        # Calculate result
        result = round(amount * rate, 2)

        return {
            "status_code": 200,
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "result": result,
            "rate": rate
        }

class UnitConversionAPI(API_base):    
    
    def is_unit_supported(self, from_unit, to_unit):
        """
        Check if the unit pair is supported.
        
        Args:
            from_unit (str): Source unit
            to_unit (str): Target unit
        
        Returns:
            bool: True if the unit pair is supported, False otherwise.
        """
        # Check if direct conversion exists
        direct_match = self.df[(self.df['from_unit'] == from_unit) & (self.df['to_unit'] == to_unit)]
        if not direct_match.empty:
            return True
        
        # Check if inverse conversion exists
        inverse_match = self.df[(self.df['from_unit'] == to_unit) & (self.df['to_unit'] == from_unit)]
        return not inverse_match.empty

    def get_conversion_rate(self, from_unit, to_unit):
        """
        Get the conversion rate for a unit pair using pandas DataFrame operations.
        
        Args:
            from_unit (str): Source unit
            to_unit (str): Target unit
        
        Returns:
            float: Conversion rate, or None if not found
        """
        # Try direct conversion first
        direct_match = self.df[(self.df['from_unit'] == from_unit) & (self.df['to_unit'] == to_unit)]
        if not direct_match.empty:
            return direct_match['rate'].iloc[0]
        
        # Try inverse conversion
        inverse_match = self.df[(self.df['from_unit'] == to_unit) & (self.df['to_unit'] == from_unit)]
        if not inverse_match.empty:
            return 1 / inverse_match['rate'].iloc[0]
        
        return None

    def execute(self, **params):
        """
        Execute unit conversion.
        
        Required params:
        - amount: float/int - Amount to convert
        - from_unit: str - Source unit
        - to_unit: str - Target unit
        
        Returns:
        - Dictionary with conversion results or error information
        """
        expected_params = {"amount", "from_unit", "to_unit"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        amount = params.get("amount")
        from_unit = params.get("from_unit")
        to_unit = params.get("to_unit")

        is_valid, error = self.validate_type(amount, "amount", (float, int))
        if not is_valid:
            return error    
        
        is_valid, error = self.validate_type(from_unit, "from_unit", str)
        if not is_valid:
            return error  

        is_valid, error = self.validate_type(to_unit, "to_unit", str)
        if not is_valid:
            return error  
        
        # Check for negative amounts - return 400 status code
        is_valid, error = self.validate_param(
            amount > 0,
            "Amount must be positive",
            400
        )
        if not is_valid:
            return error
        
        # Check if unit pair is supported
        if not self.is_unit_supported(from_unit, to_unit):
            return self.handle_error(f"Unit pair ({from_unit}, {to_unit}) not supported", 404)

        # Get conversion rate
        rate = self.get_conversion_rate(from_unit, to_unit)
        if rate is None:
            return self.handle_error(f"Conversion rate not found for ({from_unit}, {to_unit})", 404)

        # Calculate result
        result = round(amount * rate, 2)

        return {
            "status_code": 200,
            "from": from_unit,
            "to": to_unit,
            "amount": amount,
            "result": result,
            "rate": rate
        }
        
class FlightStatusAPI(API_base):
    def is_flight_available(self, date, flight_number):
        """
        Check if the flight is available on the given date.
        
        Args: 
            date (str): Date in YYYY-MM-DD format
            flight_number (str): Flight number 
        
        Returns:
            bool: True if flight is available, False if not
        """
        # Check if flight exists for the given date and flight number
        flight_match = self.df[(self.df['date'] == date) & (self.df['flight_number'] == flight_number)]
        return not flight_match.empty
    
    def execute(self, **params):
        """
        Get flight status information.
        
        Required params:
        - date (str): Date in YYYY-MM-DD format
        - flight_number (str): Flight number
        
        Returns:
        - Dictionary with flight status information or error
        """
        expected_params = {"date", "flight_number"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        date = params.get("date")
        flight_number = params.get("flight_number")
        is_valid, error = self.validate_type(date, "date", str)
        if not is_valid:
            return error
            
        is_valid, error = self.validate_type(flight_number, "flight_number", str)
        if not is_valid:
            return error 
        
        # Validate date format
        try: 
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return self.handle_error("Date must be in YYYY-MM-DD format", 400)
        
        # Check if flight is available
        if not self.is_flight_available(date, flight_number):
            return self.handle_error(f"Flight {flight_number} not found on {date}", 404)
        
        # Get flight information from DataFrame
        flight_match = self.df[(self.df['date'] == date) & (self.df['flight_number'] == flight_number)]
        flight_info = flight_match.iloc[0].to_dict()
        
        # Remove the date and flight_number from the result since they're already in the main response
        flight_info.pop('date', None)
        flight_info.pop('flight_number', None)
        
        result = {
            "status_code": 200,
            "date": date,
            "flight_number": flight_number,
            **flight_info
        }
        
        return result
       
class SongLyricsAPI(API_base):
    
    def execute(self, **params):
        """
        Search for songs by song name and optionally by singer.
        
        Required params:
        - song_name: str - Name of the song to search for
        
        Optional params:
        - singer: str - Singer name to filter by
        
        Returns:
        - Dictionary with found song(s) or error information
        """
        expected_params = {"song_name", "singer"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        song_name = params.get("song_name")
        singer = params.get("singer")
        
        # Validate parameters
        is_valid, error = self.validate_type(song_name, "song_name", str)
        if not is_valid:
            return error
        
        if singer is not None:
            is_valid, error = self.validate_type(singer, "singer", str)
            if not is_valid:
                return error
        
        # Filter by song name (case-insensitive)
        song_mask = self.df['song_name'].str.lower() == song_name.lower()
        filtered_df = self.df[song_mask]
        
        if filtered_df.empty:
            return self.handle_error(f"No songs found with title '{song_name}'", 404)
        
        # Filter by singer if provided
        if singer:
            singer_mask = filtered_df['singer'].str.lower() == singer.lower()
            filtered_df = filtered_df[singer_mask]
            
            if filtered_df.empty:
                # Check if singer exists in the database
                singer_exists = (self.df['singer'].str.lower() == singer.lower()).any()
                if singer_exists:
                    return self.handle_error(
                        f"Singer '{singer}' exists in our database but didn't sing '{song_name}'",
                        404
                    )
                else:
                    return self.handle_error(f"No songs found by singer '{singer}'", 404)
        
        # Convert DataFrame to list of dictionaries
        songs = filtered_df.to_dict('records')
        
        # Return results
        if len(songs) == 1:
            # If only one song matches, return it directly with success flag
            result = songs[0].copy()
            result["status_code"] = 200
            return result
        else:
            # If multiple songs match, return them as a list with metadata
            return {
                "status_code": 200,
                "count": len(songs),
                "message": f"Found {len(songs)} songs matching '{song_name}'" + 
                          (f" by '{singer}'" if singer else ""),
                "songs": songs
            }
                
class TimeZoneConverterAPI(API_base):
    
    def is_city_supported(self, city):
        """
        Check if a city is supported using pandas DataFrame operations.
        
        Args:
            city (str): City name (case insensitive)
        
        Returns:
            bool: True if city is supported, False otherwise
        """
        city_lower = city.lower()
        city_match = self.df[self.df['City'].str.lower() == city_lower]
        return not city_match.empty
    
    def get_city_timezone_info(self, city):
        """
        Get timezone information for a city using pandas DataFrame operations.
        
        Args:
            city (str): City name (case insensitive)
        
        Returns:
            dict: Dictionary with timezone and UTC offset, or None if not found
        """
        city_lower = city.lower()
        city_match = self.df[self.df['City'].str.lower() == city_lower]
        
        if city_match.empty:
            return None
        
        row = city_match.iloc[0]
        return {
            'timezone': row['Timezone'],
            'utc_offset': float(row['UTC_Offset'])
        }
    
    def execute(self, **params):
        """
        Convert time from current location to destination time zone.
        
        Required params:
        - destination: str - Destination city (case insensitive)
        - time: str - Time in format 'YYYY-MM-DD HH:MM AM/PM'
        - current_location: str - Current location city (case insensitive)
        
        Returns:
        - Dictionary with conversion results or error information
        """
        expected_params = {"destination", "time", "current_location"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        destination = params.get("destination")
        time_str = params.get("time")
        current_location = params.get("current_location")

        is_valid, error = self.validate_type(destination, "destination", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(current_location, "current_location", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(time_str, "time", str)
        if not is_valid:
            return error
        
        # Check if cities are supported
        if not self.is_city_supported(destination):
            return self.handle_error(f"Destination '{destination}' not supported", 404)
        
        if not self.is_city_supported(current_location):
            return self.handle_error(f"Current location '{current_location}' not supported", 404)
        
        # Validate time format
        try:
            time_obj = datetime.strptime(time_str, '%Y-%m-%d %I:%M %p')
        except ValueError:
            return self.handle_error("Time must be in the format 'YYYY-MM-DD HH:MM AM/PM'", 400)
        
        # Get timezone information for both cities
        current_info = self.get_city_timezone_info(current_location)
        destination_info = self.get_city_timezone_info(destination)
        
        if not current_info or not destination_info:
            return self.handle_error("Error retrieving timezone information", 500)
        
        # Get UTC offsets
        current_offset = current_info['utc_offset']
        destination_offset = destination_info['utc_offset']
        
        # Calculate the time difference in hours
        time_difference = destination_offset - current_offset
        
        # Convert the time from current location to destination
        # First adjust to UTC then to destination time zone
        utc_time = time_obj - timedelta(hours=current_offset)
        destination_time = utc_time + timedelta(hours=destination_offset)
        
        # Format the result time
        formatted_destination_time = destination_time.strftime('%Y-%m-%d %I:%M %p')
        
        # Prepare the sign for the time difference
        sign = "+" if time_difference > 0 else ""
        if time_difference == 0:
            sign = ""
        
        return {
            "status_code": 200,
            "destination": destination,  # Return the original case for display
            "time_in_destination": formatted_destination_time,
            "current_location_timezone": current_info['timezone'],
            "destination_timezone": destination_info['timezone'],
            "difference": f"{sign}{time_difference}"
        }

class GetCarListingByDealerships(API_base):
    def execute(self, **params):
        """
        Retrieve car listings filtered by specified dealerships.
        
        Args:
            **params: Keyword arguments containing:
                dealerships (list): List of dealership names to filter car listings by.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings for the specified 
                  dealerships (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"dealerships"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        dealerships = params.get("dealerships")
        
        is_valid, error = self.validate_type(dealerships, "dealerships", list)
        if not is_valid:
            return error

        try: 
            dealership_listing = self.df[(self.df['Car Dealership'].isin(dealerships))]

            return{
                "status_code": 200,
                "Listings": dealership_listing
            }
        except Exception as e:
            return {
                "error_code": 500,
                "error": e}

class FindDealershipsByLocation(API_base):
    def execute(self, **params):
        """
        Find all dealerships located in a specified location.
        
        Args:
            **params: Keyword arguments containing:
                location (str): The location name to search for dealerships.
                    Must match location names in the 'Location' column of the dataset.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - location (str): The location that was searched for 
                  (only present when success is True).
                - dealerships (list): List of unique dealership names found at the 
                  specified location (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"location"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        location = params.get("location")

        is_valid, error = self.validate_type(location, "location", str)
        if not is_valid:
            return error

        try:
            filtered_df = self.df[self.df['Location'] == location]

            dealerships = filtered_df['Car Dealership'].unique().tolist()
    
            return {
            "status_code": 200,
            "Location": location,
            "Dealerships": dealerships
            }   
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }
               
class FilterByCarBuild(API_base):
    def execute(self, **params):
        expected_params = {"build", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        build = params.get("build")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(build, "build", str)
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Build"].str.lower() == build.lower()]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}

class FilterByCarBrand(API_base):
    def execute(self, **params):
        """
        Filter car listings by brand type.
        
        Args:
            **params: Keyword arguments containing:
                brand (str): The brand type to filter by. Must match values in 
                    the 'Car Brand' column of the listings DataFrame.
                listings (pandas.DataFrame): DataFrame containing car listings with 
                    a 'Car Brand' column to filter on.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings matching the 
                  specified brand type (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"brand", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        brand = params.get("brand")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(brand, "brand", str)
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Car Brand"].str.lower() == brand.lower()]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class FilterByCarPrice(API_base):
    def execute(self, **params):
        """
        Filter car listings by maximum price (less than or equal to specified price).
        
        Args:
            **params: Keyword arguments containing:
                price (int or float): Maximum price threshold. Returns listings with 
                    'Ask Price' less than or equal to this value.
                listings (pandas.DataFrame): DataFrame containing car listings with 
                    an 'Ask Price' column to filter on.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings with ask price 
                  less than or equal to the specified price (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"price", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        price = params.get("price")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(price, "price", (int, float))
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Ask Price"] <= price]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class FilterByCarMileage(API_base):
    def execute(self, **params):
        """
        Filter car listings by maximum mileage (less than or equal to specified mileage).
        
        Args:
            **params: Keyword arguments containing:
                mileage (int or float): Maximum mileage threshold. Returns listings with 
                    'Mileage' less than or equal to this value.
                listings (pandas.DataFrame): DataFrame containing car listings with 
                    a 'Mileage' column to filter on.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings with mileage 
                  less than or equal to the specified mileage (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"mileage", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        mileage = params.get("mileage")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(mileage, "mileage", (int, float))
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Mileage"] <= mileage]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class FilterByCarProductionYear(API_base):
    def execute(self, **params):
        """
        Filter car listings by minimum production year (greater than or equal to specified year).
        
        Args:
            **params: Keyword arguments containing:
                year (int): Minimum production year threshold. Returns listings with 
                    'Year of Production' greater than or equal to this value.
                listings (pandas.DataFrame): DataFrame containing car listings with 
                    a 'Year of Production' column to filter on.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings with production year 
                  greater than or equal to the specified year (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"year", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        year = params.get("year")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(year, "year", int)
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Year of Production"] >= year]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class FilterByCarTitle(API_base):
    def execute(self, **params):
        """
        Filter car listings by title type (Clean or Salvage).
        
        Args:
            **params: Keyword arguments containing:
                title (str): Title type to filter by. Must match values in 
                    the 'Clean/Salvage Title' column (typically "Clean" or "Salvage").
                listings (pandas.DataFrame): DataFrame containing car listings with 
                    a 'Clean/Salvage Title' column to filter on.
        
        Returns:
            dict: A dictionary containing:
                - Status code: 200 if success
                - listings (pandas.DataFrame): Filtered car listings matching the 
                  specified title type (only present when success is True).
                - error (str or Exception): Error message or exception object 
                  (only present when success is False).
        """
        expected_params = {"title", "listings"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        title = params.get("title")
        listings = params.get("listings")

        is_valid, error = self.validate_type(listings, "listings", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(title, "title", str)
        if not is_valid:
            return error

        try: 
            filtered_df = listings[listings["Clean/Salvage Title"].str.lower() == title.lower()]
            return {
                "status_code": 200,
                "Listings": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}

class GetDate(API_base): 
    def execute(self, **params):
        """
        Retrieve date information.
        
        Args:
            **params: Keyword arguments containing:
                tag (str): The code identifier to search for in the 'Code' column.
        
        Returns:
            dict: A dictionary containing the operation result:
                - On success: {"status_code": 200 "Date": <date_value>} (date_value is a string in YYYY-MM-DD format)
                - On failure: {"status_code": 500, "error": <error_object>}
        
        Raises:
            No exceptions are raised directly. All errors are caught and 
            returned in the response dictionary under the "error" key.
        """
        expected_params = {"tag"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        tag = params.get("tag")

        try:
            cur_date = self.df[self.df['Code']==tag]['Date'].item()
            return {
                "status_code": 200,
                "Date": str(cur_date)
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }

class GetTime(API_base):
    def execute(self, **params):
        """
        Retrieve time information.
        
        
        Args:
            **params: Keyword arguments containing:
                tag (str): The code identifier to search for in the 'Code' column.
        
        Returns:
            dict: A dictionary containing the operation result:
                - On success: {"status_code": 200 "Time": <time_value>} (time_value is a string in HH:MM AM/PM format)
                - On failure: {"status_code": 500, "error": <error_object>}
        
        Raises:
            No exceptions are raised directly. All errors are caught and 
            returned in the response dictionary under the "error" key.
        """
        expected_params = {"tag"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        tag = params.get("tag")

        try:
            cur_time = self.df[self.df['Code']==tag]['Time'].item()
            return {
                "status_code": 200,
                "Time": cur_time
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }

class GetCurrentLocation(API_base):
    def execute(self, **params):
        """
        Retrieve location information.
        
        Args:
            **params: Keyword arguments containing:
                tag (str): The code identifier to search for in the 'Code' column.
        
        Returns:
            dict: A dictionary containing the operation result:
                - On success: {"status_code": 200 "Location": <location_value>}
                - On failure: {"status_code": 500, "error": <error_object>}
        
        Raises:
            No exceptions are raised directly. All errors are caught and 
            returned in the response dictionary under the "error" key.
        """
        tag = params.get("tag")

        try:
            location = self.df[self.df['Code']==tag]['Location'].item()
            return {
                "status_code": 200,
                "Location": location
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }

class GetLocation(API_base):
    def execute(self, **params):
        """
        Retrieve location information.
        
        Args:
            **params: Keyword arguments containing:
                tag (str): The code identifier to search for in the 'Code' column.
        
        Returns:
            dict: A dictionary containing the operation result:
                - On success: {"status_code": 200 "Location": <location_value>}
                - On failure: {"status_code": 500, "error": <error_object>}
        
        Raises:
            No exceptions are raised directly. All errors are caught and 
            returned in the response dictionary under the "error" key.
        """
        expected_params = {"tag"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        tag = params.get("tag")

        try:
            location = self.df[self.df['Code']==tag]['Location'].item()
            return {
                "status_code": 200,
                "Location": location
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }
class GetCurrentLocation(API_base):
    def execute(self, **params):
        """
        Retrieve location information.
        
        Args:
            **params: Keyword arguments containing:
                tag (str): The code identifier to search for in the 'Code' column.
        
        Returns:
            dict: A dictionary containing the operation result:
                - On success: {"status_code": 200 "Location": <location_value>}
                - On failure: {"status_code": 500, "error": <error_object>}
        
        Raises:
            No exceptions are raised directly. All errors are caught and 
            returned in the response dictionary under the "error" key.
        """
        expected_params = {"tag"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        tag = params.get("tag")

        try:
            location = self.df[self.df['Code']==tag]['Location'].item()
            return {
                "status_code": 200,
                "Location": location
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }        
class FindRestaurantsByLocation(API_base):
    def execute(self, **params):
        """
        Execute restaurant search by location.
        Args:
            **params: Keyword arguments containing:
                location (str): The location to search for restaurants.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - restaurants (pd.DataFrame): Filtered restaurants DataFrame if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"location"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        location = params.get("location")

        is_valid, error = self.validate_type(location, "location", str)
        if not is_valid:
            return error
            
        try: 
            restaurants_filtered_df = self.df[self.df['Location'] == location]
            return{
                "status_code": 200,
                "Restaurants": restaurants_filtered_df
            }
        except Exception as e:
            return{
                 "status_code": 500,
                 "error": e
            }    
        
class FilterByCuisine(API_base):

    def execute(self, **params):
        """
        Execute restaurant filtering by cuisine type.
        
        Args:
            **params: Keyword arguments containing:
                cuisine (str): The cuisine type to filter by.
                restaurants (pd.DataFrame): DataFrame containing restaurant data
                    with a 'Cuisine' column.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - restaurants (pd.DataFrame): Filtered restaurants DataFrame if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"cuisine", "restaurants"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        cuisine = params.get("cuisine")
        restaurants = params.get("restaurants")

        is_valid, error = self.validate_type(restaurants, "restaurants", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(cuisine, "cuisine", str)
        if not is_valid:
            return error

        try: 
            filtered_df = restaurants[restaurants["Cuisine"].str.lower() == cuisine.lower()]
            return {
                "status_code": 200,
                "Restaurants": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class FilterByRatings(API_base):

    def execute(self, **params):
        """
        Execute restaurant filtering by minimum rating.
        
        Args:
            **params: Keyword arguments containing:
                ratings (int or float): Minimum rating threshold to filter by.
                restaurants (pd.DataFrame): DataFrame containing restaurant data
                    with a 'Ratings' column.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - restaurants (pd.DataFrame): Filtered restaurants DataFrame if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"ratings", "restaurants"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        ratings = params.get("ratings")
        restaurants = params.get("restaurants")

        is_valid, error = self.validate_type(restaurants, "restaurants", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(ratings, "ratings", (int, float))
        if not is_valid:
            return error

        try: 
            filtered_df = restaurants[restaurants["Ratings"] >= ratings]
            return {
                "status_code": 200,
                "Restaurants": filtered_df
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}

class FilterByOpeningHours(API_base):
    def execute(self, **params):
        """
        Execute restaurant filtering by opening hours.
        
        Args:
            **params: Keyword arguments containing:
                time (str or datetime.time): Time to check if restaurants are open.
                    Time should be in HH:MM AM/PM format.
                restaurants (pd.DataFrame): DataFrame containing restaurant data
                    with an 'Opening Hours' column.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - restaurants (pd.DataFrame): Filtered restaurants DataFrame if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"time", "restaurants"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        time_to_check = params.get("time")
        restaurants = params.get("restaurants")

        is_valid, error = self.validate_type(restaurants, "restaurants", pd.DataFrame)
        if not is_valid:
            return error

        is_valid, error = self.validate_type(time_to_check, "time", (str, time))
        if not is_valid:
            return error

        try:
            
            mask = restaurants['Opening Hours'].apply(
                lambda hours: self._is_time_in_opening_hours(time_to_check, hours)
            )
            filtered_df = restaurants[mask]
            
            return {
                "status_code": 200,
                "Restaurants": filtered_df
            }
            
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }
    def _parse_time_string(self, time_str):
        """
        Parse time string in various formats to datetime.time object.
        Handles: '12:00 PM', '12:00PM', '15:00', '3:30 AM', etc.
        """
        time_str = time_str.strip()
        
        # Handle 24-hour format (15:00, 09:30, etc.) - must not contain AM/PM
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        
        # Handle 12-hour format with AM/PM
        am_pm_pattern = r'^(\d{1,2}):(\d{2})\s*(AM|PM)'
        match = re.match(am_pm_pattern, time_str.upper())
        
        if match:
            hour, minute, period = match.groups()
            hour, minute = int(hour), int(minute)
            
            if period == 'AM':
                if hour == 12:
                    hour = 0
            else:  # PM
                if hour != 12:
                    hour += 12
                    
            return time(hour, minute)
        
        raise ValueError(f"Cannot parse time string: {time_str}")

    def _parse_opening_hours(self, hours_str):
        """
        Parse opening hours string like '11:00 AM - 10:00 PM' into start and end times.
        Returns tuple of (start_time, end_time) as datetime.time objects.
        """
        # Split by dash and clean up
        parts = [part.strip() for part in hours_str.split(' - ')]
        if len(parts) != 2:
            raise ValueError(f"Invalid opening hours format: {hours_str}")
        
        start_str, end_str = parts
        start_time = self._parse_time_string(start_str)
        end_time = self._parse_time_string(end_str)
        
        return start_time, end_time

    def _is_time_in_opening_hours(self, check_time, opening_hours_str):
        """
        Check if a given time falls within opening hours.
        
        Args:
            check_time: Time to check (string like '12:00 PM' or '15:00', or datetime.time object)
            opening_hours_str: Opening hours string like '11:00 AM - 10:00 PM'
        
        Returns:
            bool: True if time is within opening hours, False otherwise
        """
        try:
            # Parse the time to check if it's a string
            if isinstance(check_time, str):
                check_time = self._parse_time_string(check_time)
            elif not isinstance(check_time, time):
                raise ValueError("check_time must be a string or datetime.time object")
            # Parse opening hours
            start_time, end_time = self._parse_opening_hours(opening_hours_str)
            # Handle cases where closing time is past midnight (like 5:00 PM - 12:00 AM)
            if end_time < start_time:
                # Opening hours span midnight
                return check_time >= start_time or check_time <= end_time
            else:
                # Normal case within the same day
                return start_time <= check_time <= end_time
                
        except Exception as e:
            # Return False for any parsing errors to avoid breaking the filter
            return False
        
class GetWeather(API_base):
    def execute(self, **params):
        """
        Execute weather data retrieval by location and date.
        
        Args:
            **params: Keyword arguments containing:
                location (str): The location to get weather data for.
                date (str): The date in YYYY-MM-DD format.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - temperature: Temperature value if successful.
                - description (str): Weather description if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"location", "date"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        Location = params.get("location")
        Date = params.get("date")
        
        is_valid, error = self.validate_type(Location, "location", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(Date, "date", str)
        if not is_valid:
            return error
        
        try:
            date_obj = datetime.strptime(Date, '%Y-%m-%d').date()
        except ValueError:
            return self.handle_error("time must be in YYYY-MM-DD format", 400)

        try: 
            WeatherData = self.df[(self.df['Location'] == Location) & (self.df['Date'] == Date)]
            return {
                "status_code": 200,
                "temperature": int(WeatherData.iloc[0]['Temperature']),
                "description": str(WeatherData.iloc[0]['Description'])
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e}
        
class GetAirQuality(API_base):
    def execute(self, **params):
        """
        Execute air quality data retrieval by location and date.
        
        Args:
            **params: Keyword arguments containing:
                location (str): The location to get air quality data for.
                date (str): The date in YYYY-MM-DD format.
        
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded, False otherwise.
                - quality_value: Air quality index value if successful.
                - category (str): Air quality category if successful.
                - error (str): Error message if operation failed.
        """
        expected_params = {"location", "date"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        Location = params.get("location")
        Date = params.get("date")
        
        is_valid, error = self.validate_type(Location, "location", str)
        if not is_valid:
            return error
        
        is_valid, error = self.validate_type(Date, "date", str)
        if not is_valid:
            return error
        
        try:
            date_obj = datetime.strptime(Date, '%Y-%m-%d').date()
        except ValueError:
            return self.handle_error("time must be in YYYY-MM-DD format", 400)

        try: 
            AirQualityData = self.df[(self.df['Location'].str.lower() == Location.lower()) & (self.df['Date'] == Date)]
            return {
                "status_code": 200,
                "quality_value": int(AirQualityData.iloc[0]['Quality Value']),
                "category": str(AirQualityData.iloc[0]['Category'])
            }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }

class SearchFlight(API_base):
    def execute(self, **params):
        expected_params = {"departure", "destination", "date", "time", "cabinClass", "nonstopOnly", "preferences"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        dep = params.get("departure")
        dst = params.get("destination")
        date = params.get("date")
        time = params.get("time")  # optional
        cabin = params.get("cabinClass")  # optional
        nonstop_only = params.get("nonstopOnly", False)
        preferences = params.get("preferences", {})

        # Type checks
        for name, typ in [
            ("departure", str), ("destination", str), ("date", str),
        ]:
            is_valid, err = self.validate_type(params.get(name), name, typ)
            if not is_valid: return err
        if time is not None:
            is_valid, err = self.validate_type(time, "time", str)
            if not is_valid: return err
        if cabin is not None:
            is_valid, err = self.validate_type(cabin, "cabinClass", str)
            if not is_valid: return err
        is_valid, err = self.validate_type(nonstop_only, "nonstopOnly", bool)
        if not is_valid: return err
        is_valid, err = self.validate_type(preferences, "preferences", dict)
        if not is_valid: return err

        # Basic format checks
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            return self.handle_error("date must be YYYY-MM-DD", 400)
        if time is not None:
            try:
                datetime.strptime(time, "%H:%M")
            except Exception:
                return self.handle_error("time must be HH:MM", 400)

        df = self.df[
            (self.df["departure_city"].str.casefold() == dep.casefold()) &
            (self.df["destination_city"].str.casefold() == dst.casefold()) &
            (self.df["date"] == date)
        ]
        if time:
            df = df[df["departure_time_local"] == time]
        if nonstop_only:
            df = df[df["stops"] == 0]
        if cabin:
            df = df[df["cabin_class"].str.casefold() == cabin.casefold()]

        if df.empty:
            return {"status_code": 200, "results": []}

        # Optional preference: seating
        pref_seating = preferences.get("seating")
        if isinstance(pref_seating, str):
            # Try to sort to prioritize preferred seating first
            df = pd.concat([
                df[df["seating"].str.casefold() == pref_seating.casefold()],
                df[df["seating"].str.casefold() != pref_seating.casefold()]
            ])

        results = []
        for _, r in df.iterrows():
            results.append({
                "flightNumber": r["flight_number"],
                "origin": r["departure_city"],
                "destination": r["destination_city"],
                "date": r["date"],
                "departure": r["departure_time_local"],
                "arrival": r["arrival_time_local"],
                "stops": int(r["stops"]),
                "via": r["via"] if not pd.isna(r["via"]) else None,
                "cabinClass": r["cabin_class"],
                "seating": r["seating"],
                "price": {"total": f"{float(r['price']):.2f}", "currency": "USD"},
                "seatsRemaining": int(r["seats_remaining"])
            })

        return {"status_code": 200, "results": results}
class CheckFlightStatus(API_base):
    def execute(self, **params):
        expected_params = {"flightNumber", "date"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        flight_number = params.get("flightNumber")
        date = params.get("date")
        is_valid, error = self.validate_type(flight_number, "flightNumber", str)
        if not is_valid:
            return error
        is_valid, error = self.validate_type(date, "date", str)
        if not is_valid:
            return error
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            return self.handle_error("date must be YYYY-MM-DD", 400)
        flight_match = self.df[(self.df["flight_number"].str.casefold() == flight_number.casefold()) & (self.df["date"] == date)]
        if flight_match.empty:
            return self.handle_error("Flight not found", 404)
        flight_info = flight_match.iloc[0].to_dict()
        return {
            "status_code": 200,
            "status": flight_info["status"],
            "flightNumber": flight_number,
            "date": date,
            "departureTime": flight_info["departure_time"],
            "departureLocation": flight_info["departure_location"],
            "arrivalTime": flight_info["arrival_time"],
            "destination": flight_info["destination"],
        }

class BookFlight(API_base):
    def _validate_passenger(self, p, idx):
        if not isinstance(p, dict):
            return False, self.handle_error(f"passengers[{idx}] must be an object", 400)
        name = p.get("name", {})
        dob = p.get("dob")
        iddoc = p.get("idDoc", {})
        # name
        if not isinstance(name, dict) or not isinstance(name.get("first",""), str) or not isinstance(name.get("last",""), str):
            return False, self.handle_error(f"passengers[{idx}].name.first/last required", 400)
        # dob
        if not isinstance(dob, str):
            return False, self.handle_error(f"passengers[{idx}].dob must be a string YYYY-MM-DD", 400)
        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except Exception:
            return False, self.handle_error(f"passengers[{idx}].dob must be YYYY-MM-DD", 400)
        # idDoc
        if not isinstance(iddoc, dict):
            return False, self.handle_error(f"passengers[{idx}].idDoc must be an object", 400)
        for key in ["type","number","country","expiry"]:
            if key not in iddoc or not isinstance(iddoc[key], str):
                return False, self.handle_error(f"passengers[{idx}].idDoc.{key} required (string)", 400)
        # expiry basic format check
        try:
            datetime.strptime(iddoc["expiry"], "%Y-%m-%d")
        except Exception:
            return False, self.handle_error(f"passengers[{idx}].idDoc.expiry must be YYYY-MM-DD", 400)
        return True, None

    def execute(self, **params):
        expected_params = {"flightNumber", "numberOfTickets", "passengers", "contact", "cabinClass"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        flight_no = params.get("flightNumber")
        count = params.get("numberOfTickets")
        cabin_class = params.get("cabinClass")

        if cabin_class is not None:
            is_valid, err = self.validate_type(cabin_class, "cabinClass", str)
            if not is_valid: return err
            if cabin_class not in ["ECONOMY", "BUSINESS", "FIRST"]:
                return self.handle_error("cabinClass must be ECONOMY, BUSINESS, or FIRST", 400)
            
        passengers = params.get("passengers")
        contact = params.get("contact")
        

        # Type checks
        for name, typ in [("flightNumber", str), ("numberOfTickets", int), ("passengers", list), ("contact", dict)]:
            is_valid, err = self.validate_type(params.get(name), name, typ)
            if not is_valid: return err
        if count < 1:
            return self.handle_error("numberOfTickets must be >= 1", 400)

        # Validate passengers
        for i, p in enumerate(passengers):
            ok, err = self._validate_passenger(p, i)
            if not ok: return err

        # numberOfTickets must equal passengers length
        if count != len(passengers):
            return self.handle_error("numberOfTickets must equal passengers.length", 400)

        # contact
        email = contact.get("email")
        if not isinstance(email, str) or "@" not in email:
            return self.handle_error("contact.email is required and must contain '@'", 400)

        phone = contact.get("phone")
        if phone is not None and not isinstance(phone, str):
            return self.handle_error("contact.phone must be a string if provided", 400)

        # Verify flight exists and capacity
        row = self.df[self.df["flight_number"].str.upper() == flight_no.upper()]
        if cabin_class: 
            row = row[row["cabin_class"].str.casefold() == cabin_class.casefold()]
            if row.empty:
                return self.handle_error("OFFER_NOT_FOUND: Flight not available", 404)

        row = row.iloc[0]
        seats_left = int(row["seats_remaining"])
        if count > seats_left:
            return self.handle_error("INSUFFICIENT_SEATS: Not enough seats remaining", 400)
        
        booked_cabin_class = row["cabin_class"]
        # Very simple pricing
        per = float(row["price"])
        total = round(per * count, 2)

        booking_id = f"bk_{flight_no.upper()}_001"
        tickets = [{"passengerIndex": i, "ticketNumber": f"016000000000{i+1}"} for i in range(count)]
        return {
            "status_code": 200,
            "booking": {
                "bookingId": booking_id,
                "status": "TICKETED",
                "cabinClass": booked_cabin_class,
                "currency": "USD",
                "price": { "total": f"{total:.2f}", "perTicket": f"{per:.2f}", "currency": "USD" },
                "tickets": tickets,
                "flightNumber": flight_no
            }
        }

class CancelFlight(API_base):

    def execute(self, **params):
        expected_params = {"flightNumber", "bookingId", "confirmationCode", "reason"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        flight_no = params.get("flightNumber")
        booking_id = params.get("bookingId")
        conf_code = params.get("confirmationCode")
        reason = params.get("reason")

        # Type checks
        for name, typ in [("flightNumber", str), ("bookingId", str), ("confirmationCode", str)]:
            is_valid, err = self.validate_type(params.get(name), name, typ)
            if not is_valid:
                return err


        match = self.df[
            (self.df["flight_number"] == flight_no) &
            (self.df["booking_id"] == booking_id) &
            (self.df["confirmation_code"] == conf_code)
        ]

        if match.empty:
            return self.handle_error(
                "MISMATCH: flightNumber, bookingId, or confirmationCode invalid",
                400
            )

        return {
            "status_code": 200,
            "cancellation": {
                "flightNumber": flight_no,
                "bookingId": booking_id,
                "confirmationCode": conf_code,
                "status": "CANCELED",
                "refund": { "amount": 0.00, "currency": "USD" }
            }
        }

class SearchHotel(API_base):
    """
    Search hotels by location and dates with simple filters and sorting.

    CSV columns (hotels_inventory.csv):
      hotel_id, name, city, stars, price, pool, gym, wifi,
      available_from, available_to, room_types

    sorting options: 
        PRICE_ASC, PRICE_DESC, STARS_DESC
    """

    def _parse_date(self, s, label):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            raise ValueError(f"{label} must be YYYY-MM-DD")

    def execute(self, **params):
        expected_params = {"location", "dates", "rooms", "filters", "sort"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        # Required params
        city = params.get("location")
        dates = params.get("dates")
        is_valid, err = self.validate_type(city, "city", str)
        if not is_valid: return err
        is_valid, err = self.validate_type(dates, "dates", dict)
        if not is_valid: return err

        check_in = dates.get("checkIn"); check_out = dates.get("checkOut")
        if not isinstance(check_in, str) or not isinstance(check_out, str):
            return self.handle_error("dates.checkIn and dates.checkOut are required strings", 400)
        try:
            ci = self._parse_date(check_in, "dates.checkIn")
            co = self._parse_date(check_out, "dates.checkOut")
        except ValueError as ve:
            return self.handle_error(str(ve), 400)
        if co <= ci:
            return self.handle_error("checkOut must be after checkIn", 400)

        # Optional params
        rooms = params.get("rooms") or []
        filters_ = params.get("filters") or {}
        sort = params.get("sort") or "PRICE_ASC"

        # Normalize location → city
        city_norm = str(city).strip().casefold()
        df = self.df[self.df["city"].astype(str).str.strip().str.casefold() == city_norm]

        # Availability window: (available_from <= check_in) and (available_to >= check_out)
        df = df[
            (pd.to_datetime(df["available_from"]).dt.date <= ci) &
            (pd.to_datetime(df["available_to"]).dt.date >= co)
        ]

        # Filters
        if isinstance(filters_, dict):
            stars = filters_.get("stars")
            if stars is not None:
                df = df[df["stars"] >= int(stars)]
            price_range = filters_.get("priceRange", {})
            if isinstance(price_range, dict):
                if "min" in price_range:
                    df = df[df["price"] >= float(price_range["min"])]
                if "max" in price_range:
                    df = df[df["price"] <= float(price_range["max"])]
            amenities = filters_.get("amenities", {})
            if isinstance(amenities, dict):
                for key in ["pool","gym","wifi"]:
                    val = amenities.get(key)
                    if val is True:
                        df = df[df[key] == True]

        # Sorting
        if sort == "PRICE_ASC":
            df = df.sort_values("price", ascending=True)
        elif sort == "PRICE_DESC":
            df = df.sort_values("price", ascending=False)
        elif sort == "STARS_DESC":
            df = df.sort_values("stars", ascending=False)

        # Shape output
        results = []
        for _, r in df.iterrows():
            results.append({
                "hotelId": r["hotel_id"],
                "name": r["name"],
                "city": r["city"],
                "stars": int(r["stars"]),
                "price": {"currency":"USD","nightly": float(r["price"])},
                "amenities": {"pool": bool(r["pool"]), "gym": bool(r["gym"]), "wifi": bool(r["wifi"])},
                "available": {"from": r["available_from"], "to": r["available_to"]},
                "roomTypes": str(r["room_types"]).split(",")
            })
        return {"status_code": 200, "results": results}

class BookHotel(API_base):
    """
    Book a hotel room directly with comprehensive booking details.
    - Accepts hotel_id, number_of_nights, check_details{check_in, check_out}, 
      number_of_people, personal_details{name, phone_number, email?}, 
      billing_details{name, payment_method, credit?{address, card_number, city}}
    - Returns a reservationId + confirmationCode
    """
    

    def execute(self, **params):
        expected_params = {"hotel_id", "number_of_nights", "check_details", "number_of_people", "personal_details", "billing_details"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        hotel_id = params.get("hotel_id")
        number_of_nights = params.get("number_of_nights")
        check_details = params.get("check_details")
        number_of_people = params.get("number_of_people")
        personal_details = params.get("personal_details")
        billing_details = params.get("billing_details")

        # Validate required top-level parameters
        required_params = [
            ("hotel_id", str),
            ("number_of_nights", int),
            ("check_details", dict),
            ("number_of_people", int),
            ("personal_details", dict),
            ("billing_details", dict)
        ]
        
        for param_name, param_type in required_params:
            is_valid, err = self.validate_type(params.get(param_name), param_name, param_type)
            if not is_valid: 
                return err

        # Validate number constraints
        if number_of_nights <= 0:
            return self.handle_error("number_of_nights must be positive", 400)
        if number_of_people <= 0:
            return self.handle_error("number_of_people must be positive", 400)

        # Validate check_details
        check_in = check_details.get("check_in")
        check_out = check_details.get("check_out")
        if not isinstance(check_in, str) or not check_in:
            return self.handle_error("check_details.check_in is required", 400)
        if not isinstance(check_out, str) or not check_out:
            return self.handle_error("check_details.check_out is required", 400)

        # Validate personal_details
        name = personal_details.get("name")
        phone_number = personal_details.get("phone_number")
        email = personal_details.get("email")  # Optional
        
        if not isinstance(name, str) or not name:
            return self.handle_error("personal_details.name is required", 400)
        if not isinstance(phone_number, str) or not phone_number:
            return self.handle_error("personal_details.phone_number is required", 400)
        if email is not None and not isinstance(email, str):
            return self.handle_error("personal_details.email must be string if provided", 400)

        # Validate billing_details
        billing_name = billing_details.get("name")
        payment_method = billing_details.get("payment_method")
        
        if not isinstance(billing_name, str) or not billing_name:
            return self.handle_error("billing_details.name is required", 400)
        if payment_method not in ["pay_at_desk", "credit"]:
            return self.handle_error("billing_details.payment_method must be 'pay_at_desk' or 'credit'", 400)

        # If credit payment, validate credit details
        if payment_method == "credit":
            credit_details = billing_details.get("credit")
            if not isinstance(credit_details, dict):
                return self.handle_error("billing_details.credit is required for credit payment", 400)
            
            address = credit_details.get("address")
            card_number = credit_details.get("card_number")
            city = credit_details.get("city")
            
            if not isinstance(address, str) or not address:
                return self.handle_error("billing_details.credit.address is required", 400)
            if not isinstance(card_number, str) or not card_number:
                return self.handle_error("billing_details.credit.card_number is required", 400)
            if not isinstance(city, str) or not city:
                return self.handle_error("billing_details.credit.city is required", 400)

        # Demo validation: only accept specific hotel_id
        if hotel_id not in self.df["hotel_id"].values and hotel_id != "hotel_001": 
            return self.handle_error("HOTEL_NOT_FOUND", 404)

        # Calculate total (demo pricing)
        base_rate = 99.00  # per night
        total_amount = base_rate * number_of_nights

        # Generate deterministic response
        return {
            "status_code": 200,
            "reservation": {
                "reservationId": f"res_{hotel_id}_0202",
                "confirmationCode": f"CONF-{hotel_id.upper()}-{number_of_nights:03d}",
                "status": "CONFIRMED",
                "hotel_id": hotel_id,
                "guest_name": name,
                "check_in": check_in,
                "check_out": check_out,
                "nights": number_of_nights,
                "guests": number_of_people,
                "total": {
                    "currency": "USD",
                    "amount": total_amount
                },
                "payment_method": payment_method
            }
        }

class CancelHotel(API_base):
    """
    Cancel a hotel reservation by verifying:
      - confirmation_code
      - hotel_id
      - reservation_id
      - reservation_details{last_name, phone_number_or_account}

    Initialization:
      file_path -> CSV 'hotel_cancel_keys.csv' with columns:
        hotel_id,reservation_id,confirmation_code,last_name,phone_number_or_account

    Behavior:
      - If a row matches all five fields, success=True and status=CANCELED
      - Otherwise, return a 400 MISMATCH error
    """

    def execute(self, **params):
        expected_params = {"confirmation_code", "hotel_id", "reservation_id", "reservation_details", "reason"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        confirmation_code = params.get("confirmation_code")
        hotel_id = params.get("hotel_id")
        reservation_id = params.get("reservation_id")
        reservation_details = params.get("reservation_details")
        reason = params.get("reason")  # Optional cancellation reason

        # Validate required top-level parameters
        for name, typ in [("confirmation_code", str), ("hotel_id", str), ("reservation_id", str), ("reservation_details", dict)]:
            is_valid, err = self.validate_type(params.get(name), name, typ)
            if not is_valid: 
                return err

        # Validate reservation_details nested parameters
        if not isinstance(reservation_details, dict):
            return self.handle_error("reservation_details must be a dictionary", 400)
        
        last_name = reservation_details.get("last_name")
        phone_number_or_account = reservation_details.get("phone_number_or_account")
        
        if not isinstance(last_name, str) or not last_name.strip():
            return self.handle_error("reservation_details.last_name is required", 400)
        if not isinstance(phone_number_or_account, str) or not phone_number_or_account.strip():
            return self.handle_error("reservation_details.phone_number_or_account is required", 400)

        # Normalize values for comparison (uppercase and strip whitespace)
        H = hotel_id.upper().strip()
        R = reservation_id.upper().strip()
        C = confirmation_code.upper().strip()
        L = last_name.upper().strip()
        P = phone_number_or_account.strip()  # Don't uppercase phone/account numbers

        # Search for matching record in CSV
        m = self.df[
            (self.df["hotel_id"].str.upper().str.strip() == H) &
            (self.df["reservation_id"].str.upper().str.strip() == R) &
            (self.df["confirmation_code"].str.upper().str.strip() == C) &
            (self.df["last_name"].str.upper().str.strip() == L) &
            (self.df["phone_number_or_account"].str.strip() == P)
        ]
        
        if m.empty:
            return self.handle_error("MISMATCH: confirmation_code, hotel_id, reservation_id, or reservation_details invalid", 400)

        # Build success response
        return {
            "status_code": 200,
            "cancellation": {
                "hotel_id": H,
                "reservation_id": R,
                "confirmation_code": C,
                "guest_last_name": L,
                "status": "CANCELED",
                "refund": {"currency": "USD", "amount": 0.00}
            }
        }


class CancelStoreOrder(API_base):
    """
    Cancel an e-commerce order prior to fulfillment.
    
    Parameters:
    - orderId (string): Order identifier
    - refund_method (string): "shopping_card" or "deposit_to_bank"
    - reason (string): Optional cancellation reason
    """

    def execute(self, **params):
        expected_params = {"orderId", "refund_method", "reason"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        order_id = params.get("orderId")
        refund_method = params.get("refund_method")
        reason = params.get("reason") or ""
        
        # Validate required parameters
        if not isinstance(order_id, str) or not order_id:
            return self.handle_error("orderId is required", 400)
        if refund_method not in ["shopping_card", "deposit_to_bank"]:
            return self.handle_error("refund_method must be 'shopping_card' or 'deposit_to_bank'", 400)
        if reason and not isinstance(reason, str):
            return self.handle_error("reason must be a string", 400)
        
        # Check if order exists and can be canceled
        order = self.df[self.df['order_id'] == order_id]
        if order.empty:
            return self.handle_error("Order not found", 404)
        
        order_row = order.iloc[0]
        if order_row['status'] != 'CONFIRMED':
            return self.handle_error("Order cannot be canceled - already processed", 400)
        
        # Calculate refund amount
        refund_amount = order_row['total_amount']
        
        return {
            "status_code": 200,
            "cancellation": {
                "orderId": order_id,
                "status": "CANCELED",
                "refundMethod": refund_method,
                "refundAmount": {
                    "currency": "USD",
                    "amount": refund_amount
                },
                "processedAt": "2024-08-21T10:30:00Z",
                "estimatedRefundDays": 3 if refund_method == "deposit_to_bank" else 1
            }
        }

class SearchProducts(API_base):
    """
    Search a product catalog with advanced filtering and sorting.
    
    Parameters:
    - query (string): Search query text
    - facets (object): Filtering options
      - brand (array): List of brand names to filter by
      - priceRange (object): min/max price range
      - color (array): List of colors to filter by
      - size (array): List of sizes to filter by
    - sort (string): Sort order (RELEVANCE, PRICE_ASC, PRICE_DESC)
    """

    def execute(self, **params):
        expected_params = {"query", "facets", "sort", "delivery"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        query = params.get("query", "")
        facets = params.get("facets", {})
        sort_order = params.get("sort", "RELEVANCE")
        delivery = params.get("delivery", {})

        # Validate types
        if not isinstance(query, str):
            return self.handle_error("query must be a string", 400)
        if not isinstance(facets, dict):
            return self.handle_error("facets must be an object", 400)
        if sort_order not in ["RELEVANCE", "PRICE_ASC", "PRICE_DESC"]:
            return self.handle_error("sort must be RELEVANCE, PRICE_ASC, or PRICE_DESC", 400)
        
        speed = delivery.get("speed", "STANDARD")
        country = delivery.get("country", None)
        if speed not in ["STANDARD", "EXPRESS", "standard", "express"]:
            return self.handle_error("delivery.speed must be STANDARD or EXPRESS", 400)
        if country and (not isinstance(country, str) or len(country) != 2):
            return self.handle_error("delivery.country must be a string and 2-letter country code", 400)
        # Filter products based on query
        filtered_df = self.df.copy()
        
        # Apply facet filters (case-insensitive)
        if facets.get("brand"):
            filtered_df = filtered_df[filtered_df['brand'].str.lower().isin([b.lower() for b in facets["brand"]])]
        
        if facets.get("color"):
            filtered_df = filtered_df[filtered_df['color'].str.lower().isin([c.lower() for c in facets["color"]])]
            
        if facets.get("size"):
            filtered_df = filtered_df[filtered_df['size'].str.lower().isin([s.lower() for s in facets["size"]])]
            
        if facets.get("priceRange"):
            price_range = facets["priceRange"]
            if price_range.get("min") is not None:
                filtered_df = filtered_df[filtered_df['price'] >= price_range["min"]]
            if price_range.get("max") is not None:
                filtered_df = filtered_df[filtered_df['price'] <= price_range["max"]]
        
        # Apply fuzzy matching if query exists
        if query:
            # Combine name and category for fuzzy matching
            filtered_df['search_text'] = filtered_df['name'] + ' ' + filtered_df['category']
            # Calculate fuzzy ratio for each product
            filtered_df['ratio'] = filtered_df['search_text'].apply(
                lambda x: fuzz.ratio(query.lower(), x.lower())
            )
        else:
            # If no query, set ratio to 100 for all products (no filtering)
            filtered_df['ratio'] = 100
        
        # Apply sorting with multi-key: ratio first, then price/relevance
        if sort_order == "PRICE_ASC":
            filtered_df = filtered_df.sort_values(['ratio', 'price'], ascending=[False, True])
        elif sort_order == "PRICE_DESC":
            filtered_df = filtered_df.sort_values(['ratio', 'price'], ascending=[False, False])
        else:  # RELEVANCE
            filtered_df = filtered_df.sort_values('ratio', ascending=False)
        
        # Convert to results format
        products = []
        for _, row in filtered_df.iterrows():
            products.append({
                "sku": row['sku'],
                "name": row['name'],
                "brand": row['brand'],
                "price": float(row['price']),
                "color": row['color'],
                "size": row['size'],
                "inStock": row['in_stock'],
                "description": row['description']
            })
        
        return {
            "status_code": 200,
            "results": {
                "products": products,
                "totalCount": len(products),
                "delivery": {
                    "speed": speed,
                    "country": country
                }
            }
        }
    
class SearchSKU(API_base):
    """
    Look up a product SKU by color, type, brand, and size.

    Required params:
    - color: str — Product color (e.g., "black")
    - item_name: str — Product name
    - brand: str — Brand name (e.g., "Seiko")
    - size: str — Item size; note that size varies by item category:
      - 52mm for a watches
      - S, M, L for clothing
      - Any number for shoes
      - OneSize for wallets, etc

    Guarantee:
    - Each (color, type, brand, size) combination maps to exactly one SKU.

    Returns:
    - { "status_code": 200, "sku": <string> } when a unique match is found
    - { "status_code": 404, "error": "SKU not found" } when no match is found
    - { "status_code": 409, "error": "Multiple SKUs matched" } if data contains duplicates
    """
    def execute(self, **params):
        expected_params = {"color", "item_name", "brand", "size"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        color = params.get("color")
        item_name = params.get("item_name")
        brand = params.get("brand")
        size = params.get("size")

        # Validate parameter types
        is_valid, error = self.validate_type(color, "color", str)
        if not is_valid:
            return error
        is_valid, error = self.validate_type(item_name, "item_name", str)
        if not is_valid:
            return error
        is_valid, error = self.validate_type(brand, "brand", str)
        if not is_valid:
            return error
        is_valid, error = self.validate_type(size, "size", str)
        if not is_valid:
            return error

        # Filter dataframe (case-insensitive, compare sizes as strings)
        try:
            df = self.df
            mask = (
                df['color'].astype(str).str.casefold() == str(color).casefold()
            ) & (
                df['name'].astype(str).str.casefold() == str(item_name).casefold()
            ) & (
                df['brand'].astype(str).str.casefold() == str(brand).casefold()
            ) & (
                df['size'].astype(str).str.casefold() == str(size).casefold()
            )
            matches = df[mask]

            if matches.empty:
                return {
                    "status_code": 404,
                    "error": "SKU not found"
                }

            skus = matches['sku'].astype(str).tolist()
            if len(skus) == 1:
                return {
                    "status_code": 200,
                    "sku": skus[0]
                }
            else:
                return {
                    "status_code": 409,
                    "error": "Multiple SKUs matched"
                }
        except Exception as e:
            return {
                "status_code": 500,
                "error": e
            }
class CreateCart(API_base):
    """
    Create a shopping cart with items and optional coupons.
    
    Parameters:
    - items (array): Required list of cart items
      - sku (string): Product SKU
      - qty (integer): Quantity (minimum 1)
      - variant (object): Optional product variant
        - color (string): Color variant
        - size (string): Size variant
    - coupons (array): Optional list of coupon codes
    """
    def __init__(self, products_source, coupons_source=None):
        # Initialize products dataframe to self.df
        if isinstance(products_source, pd.DataFrame):
            self.df = products_source
        else:
            super().__init__(products_source)

        # Initialize coupons dataframe to self.coupons_df
        if isinstance(coupons_source, pd.DataFrame):
            self.coupons_df = coupons_source
        elif isinstance(coupons_source, str):
            try:
                self.coupons_df = pd.read_csv(coupons_source)
            except Exception:
                self.coupons_df = pd.DataFrame()
        else:
            self.coupons_df = pd.DataFrame()

    def execute(self, **params):
        expected_params = {"items", "coupons"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        items = params.get("items")
        coupons = params.get("coupons", [])
        
        # Validate required parameters
        if not isinstance(items, list) or len(items) == 0:
            return self.handle_error("items is required and must be a non-empty array", 400)
        if not isinstance(coupons, list):
            return self.handle_error("coupons must be an array", 400)
        
        # Validate and process items
        cart_items = []
        total_amount = 0.0
        
        for item in items:
            if not isinstance(item, dict):
                return self.handle_error("each item must be an object", 400)
            
            sku = item.get("sku")
            qty = item.get("qty")
            
            if not isinstance(sku, str) or not sku:
                return self.handle_error("item.sku is required", 400)
            if not isinstance(qty, int) or qty < 1:
                return self.handle_error("item.qty must be a positive integer", 400)
            
            # Check if product exists
            product = self.df[self.df['sku'] == sku]
            if product.empty:
                return self.handle_error(f"Product with SKU {sku} not found", 404)
            
            product_row = product.iloc[0]
            if not product_row['in_stock']:
                return self.handle_error(f"Product {sku} is out of stock", 400)
            
            item_total = product_row['price'] * qty
            total_amount += item_total
            
            cart_items.append({
                "sku": sku,
                "name": product_row['name'],
                "quantity": qty,
                "unitPrice": float(product_row['price']),
                "totalPrice": float(item_total),
            })
        
        # Process coupons
        applied_coupons = []
        discount_amount = 0.0
        
        for coupon_code in coupons:
            if not isinstance(coupon_code, str):
                return self.handle_error("coupon codes must be strings", 400)
            
            if not self.coupons_df.empty:
                coupon = self.coupons_df[self.coupons_df['code'] == coupon_code]
                if not coupon.empty:
                    coupon_row = coupon.iloc[0]
                    if coupon_row['active']:
                        discount = round(coupon_row['discount_percent'] / 100 * total_amount, 2)
                        discount_amount += discount
                        applied_coupons.append({
                            "code": coupon_code,
                            "discount": discount,
                            "description": coupon_row['description']
                        })
        
        cart_id = f"cart_30303"
        total_amount = round(total_amount, 2)
        discount_amount = round(discount_amount, 2)
        final_total = max(0.0, total_amount - discount_amount)
        final_total = round(final_total, 2)

        return {
            "status_code": 200,
            "cart": {
                "cartId": cart_id,
                "items": cart_items,
                "subtotal": total_amount,
                "discounts": applied_coupons,
                "discountAmount": discount_amount,
                "total": final_total,
                "currency": "USD",
                "itemCount": sum(item["quantity"] for item in cart_items)
            }
        }

class CheckoutCart(API_base):
    """
    Checkout a cart with shipping and payment information.
    
    Parameters:
    - cartId (string): Cart identifier
    - shipping (object): Shipping information
      - address (object): Shipping address
        - line1 (string): Address line 1
        - city (string): City
        - region (string): State/region (optional)
        - postalCode (string): Postal code
        - country (string): 2-letter country code
      - method (string): STANDARD or EXPRESS
    - payment (object): Payment information
      - token (string): Payment token
    - preferences (object): Optional preferences
      - ecoPackaging (boolean): Use eco-friendly packaging
    """

    def execute(self, **params):
        expected_params = {"cartId", "shipping", "payment", "preferences"}
        unexpected_params = set(params.keys()) - expected_params
        if unexpected_params:
            return self.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
        
        cart_id = params.get("cartId")
        shipping = params.get("shipping")
        payment = params.get("payment")
        preferences = params.get("preferences", {})
        
        # Validate required parameters
        if not isinstance(cart_id, str) or not cart_id:
            return self.handle_error("cartId is required", 400)
        if not isinstance(shipping, dict):
            return self.handle_error("shipping is required", 400)
        if not isinstance(payment, dict):
            return self.handle_error("payment is required", 400)
        if not isinstance(preferences, dict):
            return self.handle_error("preferences must be an object", 400)
        
        # Validate shipping
        address = shipping.get("address")
        method = shipping.get("method")
        
        if not isinstance(address, dict):
            return self.handle_error("shipping.address is required", 400)
        if method not in ["STANDARD", "EXPRESS"]:
            return self.handle_error("shipping.method must be STANDARD or EXPRESS", 400)
        
        # Validate address fields
        required_address_fields = ["line1", "city", "country", "postalCode"]
        for field in required_address_fields:
            if not isinstance(address.get(field), str) or not address.get(field):
                return self.handle_error(f"shipping.address.{field} is required", 400)
        
        if len(address.get("country")) != 2:
            return self.handle_error("shipping.address.country must be 2-letter code", 400)
        
        # Validate payment
        token = payment.get("token")
        if not isinstance(token, str) or not token:
            return self.handle_error("payment.token is required", 400)
        
        # Check if cart exists (demo: accept any cart_id starting with "cart_")
        if not cart_id.startswith("cart_"):
            return self.handle_error("Invalid cart ID", 404)
        
        # Calculate shipping cost
        shipping_cost = 15.00 if method == "EXPRESS" else 5.00
        
        # Generate order
        order_id = f"ORD_01010"

        
        return {
            "status_code": 200,
            "order": {
                "orderId": order_id,
                "cartId": cart_id,
                "status": "CONFIRMED",
                "shipping": {
                    "address": address,
                    "method": method,
                    "cost": shipping_cost,
                    "estimatedDays": 1 if method == "EXPRESS" else 3
                },
                "payment": {
                    "status": "PROCESSED",
                    "last4": token[-4:] if len(token) >= 4 else "****"
                },
                "total": {
                    "currency": "USD",
                    "subtotal": 199.99,  # Demo value
                    "shipping": shipping_cost,
                    "total": round(199.99 + shipping_cost, 2)
                }
            }
        }

