# Import libraries
import requests
import xml.etree.ElementTree as ET
import sqlite3
import gzip
import io
import argparse

# Argument parser
parser = argparse.ArgumentParser(description='This program extracts sections and metadata of XML article from EuropePMC')


parser.add_argument("-d", "--database", help="Required. Database Name where the data will be stored. Not possible to update the database. It should have '.db' sufix",
required=True)

parser.add_argument("-i", "--input", help="Required. File with all the PMID that will be inputed to the API. If you write 'all', this script will parse all OpenAccess XML files",
required=True)

args = parser.parse_args()

# Input PMID file, if not we will parse all available PMID publications of EuropePMC
# 

# # Name of the database
DB_FILE = args.database

# # Connect to the SQLite database
# # If name not found, it will create a new database
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Never worked in supplementary material, don't know what to expect
def retrieveSupplementary(root):
    for supplementary in root.iter('supplementary-material'):
        return str(ET.tostring(supplementary)).replace('"',"'")

def retrieveMetadata(root):
    dictMetadata = {
        'issn':{'ppub':'', 'epub':''},
     'journalTitle':'',
      'publisherName':''
    }
    for front in root.iter('front'):
        for journalId in front.iter('issn'):
            if "ppub" in journalId.attrib['pub-type']:
                dictMetadata['issn']['ppub'] = ''.join(journalId.itertext())
            if "epub" in journalId.attrib['pub-type']:
                dictMetadata['issn']['epub'] = ''.join(journalId.itertext())
        for journalTitle in front.iter('journal-title'):
            dictMetadata['journalTitle'] = ''.join(journalTitle.itertext())
        for publisher in front.iter('publisher-name'):
            dictMetadata['publisherName'] = ''.join(publisher.itertext())
    return dictMetadata

# Retrieve the text for each section
def retrieveSections(root):

    dictSection = {'Intro': '', 'Method': '', 'Result': '', 'Discussion': ''}
    for body in root.iter('body'):
        for child in body.iter('sec'):
            if "sec-type" in child.attrib:
                for section in dictSection.keys(): # For each section in dictSection
                    # Sections inside sec-type are written in the following form:
                    # intro, methods, results, discussion
                    if section.lower() in child.attrib["sec-type"].lower():
                        dictSection[section] = ''.join(child.itertext()).replace('"',"'")# Text without tags
                        # dictSection[section] = ET.tostring(child) # Text with tags
            if child[0].text:
                for section, sectionData in dictSection.items():                
                    if sectionData:
                        continue
                    if section.lower() in child[0].text.lower():
                        dictSection[section] = ''.join(child.itertext()).replace('"',"'")# Text without tags
                        # dictSection[section] = ET.tostring(child) # Text with tags
    return dictSection

def commitToDatabase(pmcid, dictSection, dictMetadata, supMaterial):
    c.execute(f'''INSERT OR IGNORE INTO Main
    values ("{pmcid}", "{dictSection["Intro"]}", "{dictSection["Method"]}",
    "{dictSection["Result"]}", "{dictSection["Discussion"]}", "{supMaterial}",
     "{dictMetadata["issn"]["ppub"]}", "{dictMetadata["issn"]["epub"]}",
     "{dictMetadata["journalTitle"]}", "{dictMetadata["publisherName"]}")''')
    conn.commit()

def createDatabase():
    c.execute('''DROP TABLE IF EXISTS Main''')
    c.execute('''CREATE TABLE IF NOT EXISTS "Main" (
	            "pmcid"	TEXT NOT NULL,
	            "Introduction"	TEXT,
	            "Methods" TEXT,
	            "Result" TEXT,
	            "Discussion" TEXT,
                "SupMaterial" TEXT,
	            "ISSN PPUB" TEXT,
                "ISSN EPUB" TEXT,
                "JournalTitle" TEXT,
                "PublisherName" TEXT,
	            PRIMARY KEY("pmcid")
            )''')

def apiSearch(pmcid):
    req = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    print(req)
    r = requests.get(req)
    if not r:
        return
    root = ET.fromstring(r.content)
    if not root.findall('body'):
        return
    dictSection = retrieveSections(root)
    dictMetadata = retrieveMetadata(root)
    supMaterial = retrieveSupplementary(root)

    commitToDatabase(pmcid, dictSection, dictMetadata, supMaterial)


def main():
    dummyCounter = 0
    createDatabase()
    if args.input == "all":
        OAUrl = requests.get("https://europepmc.org/ftp/oa/pmcid.txt.gz")
        gzFile = OAUrl.content
        f = io.BytesIO(gzFile)
        with gzip.GzipFile(fileobj=f) as OAFiles:
            for OAFile in OAFiles:
                dummyCounter += 1
                apiSearch(str(OAFile[:-1],"utf-8"))
    else:
        with open(args.input, 'r') as f:
            for listFiles in f:
                dummyCounter += 1
                listFiles = listFiles.strip()
                apiSearch(listFiles)
    print(dummyCounter)


if __name__ == '__main__':
    main()