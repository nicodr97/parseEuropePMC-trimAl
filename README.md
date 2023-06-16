# parseEuropePMC-FullXML
Script to extract the text from different sections and other metadata of the available Full text XML files from EuropePMC.

It extracts the content from the following sections in text format: Introduction, Methods, Results and Discussion. You are able to change the code and extract the sections in XML format. It also retrieves the Supplementary data in XML format.

The metadata outputed is the following: ISSN PPUB, ISSN EPUB, Journal Title and Publisher Name.

All the data is then stored in a SQLite database.
 
Python 3.5 or later is needed. The script depends on standard libraries, plus the ones declared in [requirements.txt](requirements.txt).
 
 * In order to install the dependencies you need `pip` and `venv` Python modules.
	- `pip` is available in many Linux distributions (Ubuntu package `python-pip`, CentOS EPEL package `python-pip`), and also as [pip](https://pip.pypa.io/en/stable/) Python package.
	- `venv` is also available in many Linux distributions (Ubuntu package `python3-venv`). In some of these distributions `venv` is integrated into the Python 3.5 (or later) installation.

* The creation of a virtual environment and installation of the dependencies in that environment is done running:

```bash
python3 -m venv .pyDBenv
source .pyDBenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run the following command to use the script:

 
 ```
 
usage: parseXMLBioHackaton.py [-h] -d DATABASE -i INPUT

This program extracts sections and metadata of XML article from EuropePMC

options:
  -h, --help            show this help message and exit
  -d DATABASE, --database DATABASE
                        Required. Database Name where the data will be stored. Not possible to
                        update the database. It should have '.db' sufix
  -i INPUT, --input INPUT
                        Required. File with all the PMCID that will be inputed to the API. If you
                        write 'all', this script will parse all OpenAccess XML files

 ```
