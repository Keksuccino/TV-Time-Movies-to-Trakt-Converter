# TV Time Movies to Trakt Converter

This Python script makes it possible to migrate your TV Time movie data to Trakt.

Trakt for a while now has its own [Importer](https://forums.trakt.tv/t/import-from-imdb-letterboxd-tv-time-csv-or-json-files/32483), but that one can only import TV shows from TV Time and no movies, which is why this script exists!

# Getting Your TV Time Data

The first and most important step is to get your data from TV Time, since they don't allow you to export it, you need to ask them to give it to you via a GDPR data request.

1. [Send an email](mailto:support@tvtime.com?subject=GDPR%20Data%20Request&body=Hi,%20I%20would%20like%20to%20receive%20a%20copy%20of%20my%20data%20according%20to%20GDPR%20laws.) to TV Time support.
2. Check your inbox in about ~ 1-2 weeks. You'll get two emails from TV Time: one with a .zip file and another with a password to unlock it.
3. Once you have the unlocked file, you can continue with the actual script!

# The Script

To use the script, you will first need to [install Python](https://www.python.org/downloads/).

After installing Python, run this in your console to install all dependencies for the script:<br>
`pip install requests tqdm colorama`

Now [download the script](https://github.com/Keksuccino/TV-Time-Movies-to-Trakt-Converter/blob/main/tv_time_to_trakt.py) and put it in an empty folder.

After downloading the script, unpack your TV Time data, search for the `tracking-prod-records.csv` file and copy it to the folder where you saved the script in.

The final step is to open your console, then navigate to the path of the folder the script is in and then run the script via `python tv_time_to_trakt.py`.

The script should now convert all your watched movies and when it's done, it will save a file called `import_data_for_trakt.json` to the folder it is in.

# Importing the Data to Trakt

To import the converted TV Time movie data to Trakt, you need to open their [Importer](https://forums.trakt.tv/t/import-from-imdb-letterboxd-tv-time-csv-or-json-files/32483). Click on **JSON File** and drag-n-drop the `import_data_for_trakt.json` from the script folder to the field that says **Drop JSON files here or click to upload**.

Now all your movies will get imported to Trakt.
