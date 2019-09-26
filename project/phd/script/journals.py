import requests
import json
import copy
import csv
from os import path

class Journals(object):
    __csv_path = ""
    __journals = []

    #Let's check all the citations in Crossref for each of the following journals
    #I will use this API call: https://api.crossref.org/journals/<ISSN>/works
    CROSSREF_CALL = "https://api.crossref.org/journals/%s/works"

    def __init__(self, csv_path, output, input):
        self.__csv_path = csv_path
        self.output_dir = output
        self.f_name = input
        self.processed = {}

    def normalize_results(self):

        s_file = self.output_dir + self.f_name
        n_file = self.output_dir + "normalized_" + self.f_name
        sum_file = self.output_dir + "summary_" + self.f_name

        if path.exists(s_file):

            #First read s_file
            csv_reader = csv.reader(open(s_file), delimiter=',')
            next(csv_reader)
            __index = {}
            for row in csv_reader:
                if row[0] not in __index:
                    __index[row[0]] = []
                if row[1].startswith("10."):
                    __index[row[0]].append(row[1])

            #Now create the sum_file
            self.store("id,dois\n",sum_file)

            #Now create the n_file
            self.store("id,doi\n",n_file)
            for k_id in __index:
                s_dois = ""
                sum_dois = 0
                for __a_doi in __index[k_id]:
                    s_dois = s_dois + '"'+str(k_id)+'","'+str(__a_doi)+'"\n'
                    sum_dois = sum_dois + 1
                if s_dois != "":
                    s_dois = s_dois[:-1]
                    self.store(s_dois+"\n",n_file)
                self.store('"'+str(k_id)+'","'+str(sum_dois)+'"\n', sum_file)

    def build_processed_index(self):
        if path.exists(self.output_dir + self.f_name):
            csv_reader = csv.reader(open(self.output_dir + self.f_name), delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                if row[1].startswith("10."):
                    self.processed[row[0]] = "Done"
                else:
                    self.processed[row[0]] = "Error"

    def get_journals(self):
        return self.__journals

    def build_obj_from_csv(self):
        # import all the Dh Journals according to the work made by Gianmarco et.al
        journals_csv = open(self.__csv_path)
        csv_reader = csv.reader(journals_csv, delimiter=',')
        # This skips the first row of the CSV file: the header.
        #'ID', 'E_ISSN', 'P_ISSN', 'TITLE', 'URL', 'level', 'DH LEVEL', 'Iteration'
        next(csv_reader)

        for row in csv_reader:
            a_journal = {}
            a_journal['ID'] = row[0]
            a_journal['E_ISSN'] = row[1]
            a_journal['P_ISSN'] = row[2]
            a_journal['TITLE'] = row[3]
            a_journal['URL'] = row[4]
            a_journal['level'] = row[5]
            a_journal['DH LEVEL'] = row[6]
            a_journal['Iteration'] = row[7]
            self.__journals.append(a_journal)


    def crossref_req_call(self, call, issn_value, rows, offset, __dois = []):
        params = "?rows="+str(rows)+"&offset="+str(offset)
        req_call = call%issn_value
        print("Calling ... "+req_call+params)
        response = requests.get(req_call+params)
        res_dois = __dois

        if response.status_code == 200:
            json_data = json.loads(response.content)
            print("  -> Found: "+str(len(json_data['message']["items"]))+"#")
            for an_item in json_data['message']["items"]:
                if "DOI" in an_item:
                    res_dois.append(an_item["DOI"])

            if len(json_data['message']["items"]) >= rows:
                self.crossref_req_call(call, issn_value, rows, offset + rows, res_dois)
        else:
            print("  -> No results")
            return False

        return res_dois

    def store(self, str_content, dest_file = None):
        if dest_file == None:
            dest_file = self.output_dir + self.f_name
        with open(dest_file, "a") as g:
            g.write(str_content)

    def extend_journals_with_dois(self, SERVICE_CALL = "", LIMIT = -1, PRINT=True, TRY_AGAIN= False):

        ROWSXPAGE = 500
        REQ_CALL = ""
        if SERVICE_CALL == "crossref":
            REQ_CALL = self.CROSSREF_CALL

        self.build_processed_index()

        #store in a csv the results
        if PRINT and not path.exists(self.output_dir + self.f_name):
            HEADER = "id,doi"
            self.store(HEADER+"\n")

        LIMIT_LOOP = LIMIT
        extended_journals = copy.deepcopy(self.__journals)
        for a_journal_obj in extended_journals:

            if a_journal_obj["ID"] in self.processed:
                status = "Done"
                if TRY_AGAIN:
                    status = self.processed[a_journal_obj["ID"]]
                if status == "Done":
                    print(a_journal_obj["ID"]+" already processed!")
                    continue
                print(a_journal_obj["ID"]+" Try again the call!")
            else:
                #COMMENT this after testitng
                if LIMIT_LOOP != 0:
                    LIMIT_LOOP = LIMIT_LOOP - 1
                else:
                    break

            #try both ISSNs
            s = ""
            all_dois_index = []
            for issn_attr in ["E_ISSN","P_ISSN"]:

                a_journal_obj[issn_attr] = {"value": a_journal_obj[issn_attr], "in": False, "dois":[]}

                issn_value_parts = a_journal_obj[issn_attr]["value"].split(";")
                for issn_value in issn_value_parts:
                    if (issn_value != "") and (issn_value != None):

                        res = self.crossref_req_call(REQ_CALL, issn_value, ROWSXPAGE, 0, [])
                        if res != False:
                            a_journal_obj["in"] = True
                            a_journal_obj[issn_attr]["dois"] = res
                            for res_doi in res:
                                if res_doi not in all_dois_index:
                                    all_dois_index.append(res_doi)
                        else:
                            s = "error-or-not-found"
            if PRINT:

                if len(all_dois_index) > 0:
                    if s == "error-or-not-found":
                        s=""

                for a_doi in all_dois_index:
                    s = s + '"' + a_journal_obj["ID"] + '",' +'"'+a_doi+'"\n'

                if s != "":
                    if s == "error-or-not-found":
                        s = '"'+a_journal_obj["ID"]+'","error_or_not_found"'
                    else:
                        s = s[:-1]
                else:
                    s = '"'+a_journal_obj["ID"]+'",""'

                all_dois_index = []
                self.store(s+"\n")

        self.__journals = extended_journals
