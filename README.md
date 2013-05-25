# mclogalyzer #

This is a small python script to analyze your Minecraft Server log file and to
generate some nice statistics as HTML-File.

mclogalyzer is free software and available under the GPL license.

## Installation ##

To run mclogalyzer you need jinja2 as template engine. You can install it with
pip:

```
pip install jinja2
```

Then you can install mclogalyzer with the `setup.py` script:

```
python setup.py install 
```

Now you can run it with `mclogalyzer`.

Alternatively you can directly run the script `mclogalyzer/mclogalyzer.py`.

## How to use the script ##

You have to pass the path to the Minecraft Server log file and the path to an
output HTML-File to the script:

```
mclogalyzer server.log stats.html
```

Per default the script searches for a template (to generate the output file) in
the directory of the `mclogalyzer.py` script. You can also use your own
template file by specifying the option `-t template.html` or
`--template=template.html`.

You can also skip a part of the log file by specifying a time where the script
should start analyzing. To do this use the `--since` parameter. You have to
specify the time in the format `year-month-day hour:minute:second`, for example
`--since="2013-05-16 00:00:00"`.
