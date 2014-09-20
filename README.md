# MCLogalyzer #

This is a small Python script to analyze your Minecraft server log file and to
generate some nice statistics as HTML-File.

MCLogalyzer is free software and available under the GPL license.

## Installation ##

To run MCLogalyzer you need jinja2 as template engine. You can install it with
pip:

```
pip install jinja2
```

Then you can install MCLogalyzer with the `setup.py` script:

```
python setup.py install 
```

Now you can run it with `mclogalyzer`.

Alternatively you can directly run the script `mclogalyzer/mclogalyzer.py`.

## How to use the script ##

You have to pass the path to the Minecraft server log directory and the path to an
output HTML-File to the script:

```
mclogalyzer server/logs stats.html
```

Per default the script searches for a template (to generate the output file) in
the directory of the `mclogalyzer.py` script. You can also use your own
template file by specifying the option `-t template.html` or
`--template=template.html`.

You can also skip a part of the log file by specifying a time where the script
should start analyzing. To do this use the `--since` parameter. You have to
specify the time in the format `year-month-day hour:minute:second`, for example
`--since="2013-05-16 00:00:00"`. Or, you can simply use `--month` or `--week` 
to generate the report of last month or last week.

You can use the whitelist as a guide using `--w whitelist.json`. If so, users
not included in the whitelist will be removed from final results, and users not
present in log file but present in whitelist will be added to the output.
