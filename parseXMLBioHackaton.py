# Import libraries
import requests
import xml.etree.ElementTree as ET
import sqlite3
import gzip
import io
import argparse
import re
import pandas as pd
import time

# Argument parser
parser = argparse.ArgumentParser(description='This program extracts sections and metadata of XML article from EuropePMC')


parser.add_argument("-d", "--database", help="Required. Database Name where the data will be stored. Not possible to update the database. It should have '.db' sufix",
required=True)

parser.add_argument("-i", "--input", help="Required. File with all the PMID that will be inputed to the API. If you write 'all', this script will parse all OpenAccess XML files",
required=True)

parser.add_argument("--pmc", default = False, action = "store_true", help="Pass PMIDs instead of PMCIDs",
required=False)

args = parser.parse_args()

if args.pmc:
    pmc_ids = pd.read_csv("PMC-ids.csv", usecols=["PMCID","PMID"], index_col="PMID")

# Input PMID file, if not we will parse all available PMID publications of EuropePMC
# 

# # Name of the database
DB_FILE = args.database

# # Connect to the SQLite database
# # If name not found, it will create a new database
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
num_requests = 0

def pmid_to_pmcid(input_id):
    try:
        pmcid = pmc_ids.loc[input_id]
    except:
        return 0
    return pmcid.values[0]


def retrieveMetadata(root):
    dictMetadata = {'year': '', 'keywords': list()}
    for front in root.iter('front'):
        for meta in front.iter('article-meta'):
            for pubdate in meta.iter('pub-date'):
                if "pub-type" in pubdate.attrib and pubdate.attrib["pub-type"] =="epub":
                    dictMetadata['year'] = pubdate.find('year').text
            for keyword_group in meta.iter('kwd-group'):
                for keyword in keyword_group.findall("kwd"):
                    if keyword.text != None and keyword.text != "\n":
                        clean_keyword = keyword.text.replace("'", "")
                        clean_keyword = clean_keyword.replace('"', "")
                        dictMetadata['keywords'].append(clean_keyword)
                    else:
                        italic_keyword = keyword.find('italic')
                        if italic_keyword != None:
                            dictMetadata['keywords'].append(italic_keyword.text)

    return dictMetadata


# Retrieve the text for each section
def retrieveSections(root):
    dictSection = {'Method': ''}
    trimal_version = 0
    trimal_params = set()
    for body in root.iter('body'):
        for child in body.iter('sec'):
            if "sec-type" in child.attrib:
                for section in dictSection.keys(): # For each section in dictSection
                    # Sections inside sec-type are written in the following form:
                    # intro, methods, results, discussion
                    sec_type = child.attrib["sec-type"].lower()
                    section_names = [section.lower(), "phylo"]
                    if any(section_name in sec_type for section_name in section_names):
                        section_content = ''.join(child.itertext()).replace('"',"'")# Text without tags
                        trimAl_indices = [m.start() for m in re.finditer('trima(l|i)', section_content.lower())]
                        filtered_dictSection = "[...] " if len(trimAl_indices) > 0 else ""
                        for ind in trimAl_indices:
                            filtered_dictSection = filtered_dictSection +  section_content[ind-250:ind] + section_content[ind:ind+250] + " [...] "
                            if trimal_version == 0:
                                trimal_version_search =  re.search(r'trima(l|i) v(ersion|.|) ?([0-9].[0-9])', filtered_dictSection.lower())
                                if trimal_version_search is not None:
                                    trimal_version = trimal_version_search.group(3)
                            parameters = ["automated1", "-gt", "-st", "-cons", "-seqoverlap", "resoverlap", "gappyout", "strict", "strictplus", "nogaps"]
                            for param in parameters:
                                if re.search(param + r'\W', filtered_dictSection):
                                    trimal_params.add(param)
                        dictSection[section] = dictSection[section] + filtered_dictSection
                        # dictSection[section] = ET.tostring(child) # Text with tags
            if child[0].text:
                for section, sectionData in dictSection.items(): 
                    #method_section_alt_names = ["phylo", "trimm", "msa", "filter", "method"]
                    child_text = child[0].text.lower()
                    section_names = [section.lower(), "phylo"]
                    if any(section_name in child_text for section_name in section_names):
                        section_content = ''.join(child.itertext()).replace('"',"'")# Text without tags
                        trimAl_indices = [m.start() for m in re.finditer('trima(l|i)', section_content.lower())]
                        filtered_dictSection = "[...] " if len(trimAl_indices) > 0 else ""
                        for ind in trimAl_indices:
                            filtered_dictSection = filtered_dictSection +  section_content[ind-250:ind] + section_content[ind:ind+250] + " [...] "
                            if trimal_version == 0:
                                trimal_version_search =  re.search(r'trima(l|i) v(ersion|.|) ?([0-9].[0-9])', filtered_dictSection.lower())
                                if trimal_version_search is not None:
                                    trimal_version = trimal_version_search.group(3)
                            parameters = ["automated1", "-gt", "-st", "gappyout", "strict", "strictplus", "nogaps"]
                            for param in parameters:
                                if re.search(param + r'\W', filtered_dictSection):
                                    trimal_params.add(param)
                        dictSection[section] = dictSection[section] + filtered_dictSection
                        # dictSection[section] = ET.tostring(child) # Text with tags
    dictSection['parameters'] = list(trimal_params)
    dictSection['version'] = trimal_version
    return dictSection

def commitToDatabase(pmcid, dictSection, dictMetadata):
    c.execute(f'''INSERT OR IGNORE INTO Main
    values ("{pmcid}", "{dictSection["Method"]}", "{dictSection["version"]}", "{dictSection["parameters"]}", " {dictMetadata["keywords"]}", "{dictMetadata["year"]}")''')
    conn.commit()

def createDatabase():
    c.execute('''DROP TABLE IF EXISTS Main''')
    c.execute('''CREATE TABLE IF NOT EXISTS "Main" (
	            "pmcid"	TEXT NOT NULL,
	            "methods" TEXT,
                "version" TEXT,
                "parameters" TEXT,
                "keywords" TEXT,
                "year" TEXT,
	            PRIMARY KEY("pmcid")
            )''')

def apiSearch(pmcid):
    global num_requests
    if args.pmc:
        pmcid = pmid_to_pmcid(int(pmcid))
        if pmcid == 0:
            return
    if num_requests % 10 == 0:
        time.sleep(1)
    req = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    try:
        r = requests.get(req, timeout=3)
    except:
        time.sleep(60)
        try:
            r = requests.get(req)
        except:
            print("Ignored " + pmcid)
    num_requests += 1
    if r == None or not r:
        return
    root = ET.fromstring(r.content)
    if not root.findall('body'):
        return
    dictSection = retrieveSections(root)
    dictMetadata = retrieveMetadata(root)

    commitToDatabase(pmcid, dictSection, dictMetadata)
    print(pmcid)


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